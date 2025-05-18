import asyncio
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect, Depends, status
from typing import Any

from api.auth.auth_handler import decode_jwt
from repositories.message_repository import MessageRepository
from websockets_server.services.connection_manager import ConnectionManager
from websockets_server.services.rabbitmq_service import RabbitMQService
from websockets_server.dto import (
    ConnectionStatusMessage,
    UserMessage,
    MessageReceivedConfirmation,
    AIResponseMessage,
    ErrorMessage,
)
from lawly_db.db_models.db_session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

connection_manager = ConnectionManager()
rabbitmq_service = RabbitMQService()


async def handle_ai_response(data: dict[str, Any]):
    """
    Обработка ответа от AI

    :param data: Данные ответа
    """
    user_id = data.get("user_id")
    message_id = data.get("message_id")
    content = data.get("content")

    response = AIResponseMessage(
        user_id=user_id, message_id=message_id, content=content
    )

    await connection_manager.send_message(response, user_id)


async def websocket_endpoint(
    websocket: WebSocket, token: str, session: AsyncSession = Depends(get_session)
):
    """
    Обработчик WebSocket соединений
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

    # Создаем репозиторий для работы с сообщениями
    message_repo = MessageRepository(session)

    # Подключаемся к RabbitMQ, если еще не подключены
    await rabbitmq_service.connect()

    # Переменная для хранения задачи подписки
    subscription_task = None

    try:
        # Отправляем подтверждение подключения
        status_message = ConnectionStatusMessage(status="connected", user_id=user_id)
        await websocket.send_json(status_message.dict())

        # Запускаем слушателя ответов от AI
        async def response_callback(data):
            await handle_ai_response(data)

        # Используем асинхронную задачу для прослушивания ответов
        subscription_task = asyncio.create_task(
            rabbitmq_service.listen_for_responses(user_id, response_callback)
        )

        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"Получены данные от клиента: {data}")

                user_message = UserMessage(**data)

                if user_message.type == "user_message":
                    if not user_message.content:
                        continue

                    stored_message = await message_repo.create_user_ai_message(
                        user_id=user_id, content=user_message.content
                    )
                    message_id = str(stored_message.id)

                    confirmation = MessageReceivedConfirmation(
                        message_id=message_id, status="processing"
                    )
                    await websocket.send_json(confirmation.dict())

                    # Отправляем запрос через RabbitMQ
                    await rabbitmq_service.send_ai_request(
                        user_id=user_id,
                        message=user_message.content,
                        message_id=message_id,
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket отключен для пользователя {user_id}")
                break

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON: {str(e)}")
                error_message = ErrorMessage(message="Некорректный формат JSON")
                try:
                    await websocket.send_json(error_message.dict())
                except Exception:
                    logger.error(
                        "Не удалось отправить сообщение об ошибке - соединение закрыто"
                    )
                    break

            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                try:
                    error_message = ErrorMessage(message="Внутренняя ошибка сервера")
                    await websocket.send_json(error_message.dict())
                except Exception:
                    logger.error(
                        "Не удалось отправить сообщение об ошибке - соединение закрыто"
                    )
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket отключен для пользователя {user_id}")
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
