import asyncio
import logging
from typing import Any

from lawly_db.db_models.db_session import create_session

from services.ai_client_service import AIClientService
from repositories.message_repository import MessageRepository
from websockets_server.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)


class AIWorker:
    """
    Фоновый рабочий процесс для обработки запросов к AI
    """

    def __init__(self):
        self.rabbitmq_service = RabbitMQService()
        self.ai_client = AIClientService()
        self.running = False

    async def process_message(self, data: dict[str, Any]):
        """
        Обработка сообщения из очереди

        :param data: Данные запроса (user_id, message, message_id)
        """
        user_id = data.get("user_id")
        message_text = data.get("message")
        message_id = data.get("message_id")

        logger.info(
            f"Обработка запроса к AI: user_id={user_id}, message_id={message_id}"
        )

        try:
            logger.info(f"Отправка запроса к AI через gRPC: {message_text[:50]}...")
            ai_response = await self.ai_client.send_message(message_text)
            logger.info(
                f"Получен ответ от AI для сообщения {message_id}: {ai_response[:50]}..."
            )

            # Отправляем ответ обратно через RabbitMQ
            await self.rabbitmq_service.send_ai_response(
                user_id=user_id, message_id=message_id, content=ai_response
            )

            # Сохраняем ответ в базе данных
            async with create_session() as session:
                message_repo = MessageRepository(session)
                await message_repo.create_ai_response_message(
                    user_id=user_id, content=ai_response
                )
                logger.info(
                    f"Ответ AI сохранен в базе данных для пользователя {user_id}"
                )
        except Exception as e:
            logger.error(f"Ошибка обработки запроса к AI: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

    async def start(self):
        """
        Запуск воркера
        """
        if self.running:
            return

        self.running = True
        logger.info("Запуск AI воркера...")

        try:
            await self.rabbitmq_service.connect()

            await self.rabbitmq_service.start_ai_worker(self.process_message)

            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Ошибка в AI воркере: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
        finally:
            self.running = False
            await self.rabbitmq_service.close()
            logger.info("AI воркер остановлен")

    async def stop(self):
        """
        Остановка воркера
        """
        self.running = False
        logger.info("Запрошена остановка AI воркера")
