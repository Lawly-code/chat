import logging
from typing import Callable, Dict, Any

from websockets_server.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)


class MessageQueueService:
    """
    Совместимый с Redis интерфейс сервиса очереди сообщений, использующий RabbitMQ
    """

    def __init__(self):
        self.rabbitmq = RabbitMQService()
        self.queue_name = "ai_message_queue"  # Для совместимости
        self.processing = False

    async def connect(self):
        """
        Установка соединения с RabbitMQ
        """
        await self.rabbitmq.connect()
        logger.info("Соединение с RabbitMQ установлено (через MessageQueueService)")

    async def disconnect(self):
        """
        Закрытие соединения с RabbitMQ
        """
        await self.rabbitmq.close()
        logger.info("Соединение с RabbitMQ закрыто (через MessageQueueService)")

    async def add_message_to_queue(
        self, user_id: int, message: str, message_id: str
    ) -> bool:
        """
        Добавление сообщения в очередь

        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param message_id: ID сообщения
        :return: Успешность добавления
        """
        return await self.rabbitmq.add_message_to_queue(user_id, message, message_id)

    async def publish_response(self, user_id: int, message: Dict[str, Any]):
        """
        Публикация ответа для WebSocket

        :param user_id: ID пользователя
        :param message: Сообщение для отправки
        """
        await self.rabbitmq.publish_response(user_id, message)

    async def start_processing(self, process_message: Callable):
        """
        Запуск обработки сообщений из очереди

        :param process_message: Функция обработки сообщения
        """
        await self.rabbitmq.start_processing(process_message)

    async def stop_processing(self):
        """
        Остановка обработки сообщений
        """
        await self.rabbitmq.stop_processing()
