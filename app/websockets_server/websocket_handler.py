import asyncio
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, Any

from api.auth.auth_handler import decode_jwt
from repositories.message_repository import MessageRepository
from services.ai_client_service import AIClientService
from websockets_server.services.rabbitmq_service import RabbitMQService
from .connection_manager import ConnectionManager
from lawly_db.db_models.db_session import get_session, create_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

connection_manager = ConnectionManager()
rabbitmq_service = RabbitMQService()
ai_client = AIClientService()


async def handle_ai_response(data: Dict[str, Any]):
    """
    Обработка ответа от AI
    
    :param data: Данные ответа от AI
    """
    user_id = data.get("user_id")
    
    # Отправляем сообщение пользователю через WebSocket
    await connection_manager.send_message(data, user_id)
    logger.info(f"Сообщение отправлено клиенту, user_id: {user_id}")


async def subscribe_to_responses(user_id: int):
    """
    Подписка на ответы для конкретного пользователя через RabbitMQ
    
    :param user_id: ID пользователя
    """
    logger.info(f"Запуск подписки на ответы для пользователя {user_id}")
    
    try:
        # Подключаемся к RabbitMQ
        await rabbitmq_service.connect()
        logger.info(f"Соединение с RabbitMQ установлено для пользователя {user_id}")
        
        # Функция обратного вызова для обработки ответов
        async def response_callback(data):
            await handle_ai_response(data)
        
        # Запускаем прослушивание ответов
        await rabbitmq_service.listen_for_responses(user_id, response_callback)
        logger.info(f"Подписка на ответы запущена для пользователя {user_id}")
        
        # Бесконечный цикл, чтобы задача не завершалась
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.warning(f"Подписка на ответы для пользователя {user_id} отменена")
            raise
        
    except Exception as e:
        logger.error(f"Ошибка при подписке на ответы: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


async def process_message_from_queue(message_item: Dict[str, Any]):
    """
    Обработка сообщения из очереди
    
    :param message_item: Элемент очереди
    """
    try:
        user_id = message_item["user_id"]
        message_text = message_item["message"]
        message_id = message_item["message_id"]
        
        logger.info(f"Обработка сообщения {message_id} для пользователя {user_id}")
        
        # Получаем ответ от AI через gRPC
        ai_response = await ai_client.send_message(message_text)
        logger.info(f"Получен ответ от AI для сообщения {message_id}")
        
        # Отправляем ответ через RabbitMQ
        await rabbitmq_service.send_ai_response(user_id, message_id, ai_response)
        logger.info(f"Ответ отправлен через RabbitMQ для пользователя {user_id}")
        
        # Сохраняем ответ в базе данных
        try:
            # Это должно выполняться в отдельной транзакции
            async with create_session() as session:
                message_repo = MessageRepository(session)
                await message_repo.create_ai_response_message(
                    user_id=user_id,
                    content=ai_response
                )
                logger.info(f"Ответ AI сохранен в базе данных для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка сохранения ответа в БД: {str(e)}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения из очереди: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


# Запускаем обработчик очереди для воркера (используется только в воркере)
async def start_queue_processor():
    """
    Запуск обработчика очереди сообщений
    """
    await rabbitmq_service.start_ai_worker(process_message_from_queue)


# Обработчик WebSocket соединений
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Обработчик WebSocket соединений
    
    :param websocket: WebSocket соединение
    :param token: JWT токен для аутентификации
    :param session: Сессия базы данных
    """
    logger.info(f"Новое WebSocket соединение с токеном: {token[:10]}...")
    
    # Проверяем токен
    payload = decode_jwt(token)
    if not payload:
        logger.warning("Невалидный токен, закрываем соединение")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = payload["user_id"]
    logger.info(f"Авторизован пользователь ID: {user_id}")
    
    # Устанавливаем соединение
    await connection_manager.connect(websocket, user_id)
    logger.info(f"Соединение установлено для пользователя {user_id}")
    
    # Переменная для хранения задачи подписки
    subscription_task = None
    
    try:
        # Отправляем подтверждение подключения
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "user_id": user_id
        })
        
        # Запускаем подписку на ответы в отдельной задаче
        subscription_task = asyncio.create_task(subscribe_to_responses(user_id))
        logger.info(f"Задача подписки запущена для пользователя {user_id}")
        
        # Обрабатываем входящие сообщения
        while True:
            logger.info(f"Ожидание сообщений от клиента, user_id: {user_id}")
            try:
                data = await websocket.receive_json()
                logger.info(f"Получены данные от клиента: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON: {str(e)}")
                continue
            
            if data.get("type") == "user_message":
                message_text = data.get("content", "")
                if not message_text:
                    logger.warning("Получено пустое сообщение, пропускаем")
                    continue
                
                logger.info(f"Обработка сообщения от пользователя {user_id}: {message_text[:50]}...")
                
                try:
                    # Сохраняем сообщение в базе данных
                    message_repo = MessageRepository(session)
                    user_message = await message_repo.create_user_ai_message(
                        user_id=user_id,
                        content=message_text
                    )
                    
                    message_id = str(user_message.id)
                    logger.info(f"Сообщение сохранено в БД, ID: {message_id}")
                    
                    # Отправляем подтверждение о получении сообщения
                    await websocket.send_json({
                        "type": "message_received",
                        "message_id": message_id,
                        "status": "processing"
                    })
                    logger.info(f"Подтверждение отправлено, message_id: {message_id}")
                    
                    # Отправляем запрос в RabbitMQ
                    await rabbitmq_service.send_ai_request(
                        user_id=user_id,
                        message=message_text,
                        message_id=message_id
                    )
                    logger.info(f"Сообщение отправлено в RabbitMQ, message_id: {message_id}")
                
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Ошибка при обработке сообщения"
                        })
                    except:
                        pass
            
            # Даем возможность другим задачам выполниться
            await asyncio.sleep(0.1)
                
    except WebSocketDisconnect as e:
        # При разрыве соединения отменяем задачу подписки
        logger.error(f"WebSocketDisconnect: код {getattr(e, 'code', 'unknown')}, причина: '{getattr(e, 'reason', '')}'")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket соединении: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if subscription_task and not subscription_task.done():
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
        connection_manager.disconnect(websocket, user_id)
        logger.info(f"Соединение закрыто для пользователя {user_id}")
