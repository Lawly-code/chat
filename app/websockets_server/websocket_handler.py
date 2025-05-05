import asyncio
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, Any

from api.auth.auth_handler import decode_jwt
from repositories.message_repository import MessageRepository
from services.ai_client_service import AIClientService
from services.message_queue_service import MessageQueueService
from .connection_manager import ConnectionManager
from lawly_db.db_models.db_session import get_session, create_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Создаем экземпляр менеджера соединений
connection_manager = ConnectionManager()
# Создаем экземпляр сервиса очереди сообщений
message_queue = MessageQueueService()
# Создаем экземпляр AI клиента
ai_client = AIClientService()


async def subscribe_to_responses(user_id: int):
    """
    Подписка на ответы для конкретного пользователя - использует опрос Redis вместо PubSub
    
    :param user_id: ID пользователя
    """
    logger.info(f"Запуск подписки на ответы для пользователя {user_id}")
    
    try:
        # Подключаемся к Redis
        await message_queue.connect()
        logger.info(f"Соединение с Redis установлено для пользователя {user_id}")
        
        # Ключ для хранения ответов для пользователя
        response_key = f"user_responses:{user_id}"
        
        try:
            while True:
                # Проверяем, есть ли новые ответы
                if await message_queue.redis.exists(response_key):
                    # Получаем все ответы из списка
                    responses = await message_queue.redis.lrange(response_key, 0, -1)
                    
                    if responses:
                        # Удаляем полученные ответы из списка
                        await message_queue.redis.ltrim(response_key, len(responses), -1)
                        
                        # Обрабатываем каждый ответ
                        for response_data_bytes in responses:
                            try:
                                # Декодируем и парсим JSON
                                response_data = json.loads(response_data_bytes.decode('utf-8'))
                                logger.info(f"Получены данные ответа: {response_data}")
                                
                                # Отправляем ответ пользователю
                                await connection_manager.send_message(response_data, user_id)
                                logger.info(f"Сообщение отправлено клиенту, user_id: {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка обработки ответа: {str(e)}")
                
                # Пауза между проверками
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            logger.warning(f"Подписка на ответы для пользователя {user_id} отменена")
            raise
        except Exception as e:
            logger.error(f"Ошибка при обработке ответов: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    except Exception as e:
        logger.error(f"Ошибка при подключении к Redis: {str(e)}")
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
        
        # Формируем сообщение с ответом
        response_data = {
            "type": "ai_response",
            "message_id": message_id,
            "user_id": user_id,
            "content": ai_response
        }
        
        # Публикуем ответ для пользователя
        await message_queue.publish_response(user_id, response_data)
        logger.info(f"Ответ опубликован для пользователя {user_id}")
        
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


# Запускаем обработчик очереди
async def start_queue_processor():
    """
    Запуск обработчика очереди сообщений
    """
    await message_queue.start_processing(process_message_from_queue)


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
            
            # Проверяем, что это сообщение для AI
            if data.get("type") == "user_message":
                # Получаем текст сообщения
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
                    
                    # Добавляем сообщение в очередь
                    await message_queue.add_message_to_queue(
                        user_id=user_id,
                        message=message_text,
                        message_id=message_id
                    )
                    logger.info(f"Сообщение добавлено в очередь, message_id: {message_id}")
                
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
        # Отменяем задачу подписки при любом исходе
        if subscription_task and not subscription_task.done():
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass
        # Отключаем соединение
        connection_manager.disconnect(websocket, user_id)
        logger.info(f"Соединение закрыто для пользователя {user_id}")
