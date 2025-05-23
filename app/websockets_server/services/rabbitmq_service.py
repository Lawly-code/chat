import json
import logging
import aio_pika
import asyncio
from typing import Callable, Any, Optional, Dict
from aio_pika import Connection, Channel, Queue, Message, ExchangeType

from config import settings

logger = logging.getLogger(__name__)


class RabbitMQService:
    """
    Сервис для работы с RabbitMQ
    """

    def __init__(self):
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.ai_request_queue: Optional[Queue] = None
        self.response_exchange = None
        self.callback_queue: Optional[Queue] = None
        self.processing = False

        # Очереди и обмены
        self.ai_request_queue_name = "ai_request_queue"
        self.response_exchange_name = "ai_response_exchange"

    async def connect(self) -> bool:
        """
        Установка соединения с RabbitMQ

        :return: Успешность подключения
        """
        if self.connection and not self.connection.is_closed:
            return True

        try:
            # Подключаемся к RabbitMQ
            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_settings.url
            )
            self.channel = await self.connection.channel()

            # Создаем очередь запросов
            self.ai_request_queue = await self.channel.declare_queue(
                self.ai_request_queue_name, durable=True
            )

            # Создаем обмен для ответов
            self.response_exchange = await self.channel.declare_exchange(
                self.response_exchange_name, ExchangeType.DIRECT, durable=True
            )

            logger.info("Подключение к RabbitMQ успешно установлено")
            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к RabbitMQ: {str(e)}")
            return False

    async def close(self):
        """
        Закрытие соединения с RabbitMQ
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Соединение с RabbitMQ закрыто")

    async def add_message_to_queue(
        self, user_id: int, message: str, message_id: str
    ) -> bool:
        """
        Добавление сообщения в очередь AI запросов

        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param message_id: ID сообщения
        :return: Успешность добавления
        """
        # Используем send_ai_request для добавления в очередь
        return await self.send_ai_request(user_id, message, message_id)

    async def send_ai_request(
        self, user_id: int, message: str, message_id: str
    ) -> bool:
        """
        Отправка запроса к AI через RabbitMQ

        :param user_id: ID пользователя
        :param message: Сообщение для AI
        :param message_id: ID сообщения
        :return: Успешность отправки
        """
        if not await self.connect():
            logger.error("Не удалось подключиться к RabbitMQ")
            return False

        try:
            # Формируем данные для запроса
            data = {"user_id": user_id, "message": message, "message_id": message_id}

            # Создаем сообщение
            message_body = json.dumps(data).encode()
            rabbit_message = Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )

            # Отправляем сообщение в очередь
            await self.channel.default_exchange.publish(
                rabbit_message, routing_key=self.ai_request_queue_name
            )

            logger.info(f"Запрос к AI отправлен, ID сообщения: {message_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки запроса к AI: {str(e)}")
            return False

    async def listen_for_responses(
        self, user_id: int, callback: Callable[[dict[str, Any]], Any]
    ):
        """
        Прослушивание ответов от AI для определенного пользователя

        :param user_id: ID пользователя
        :param callback: Функция обратного вызова для обработки ответов
        """
        if not await self.connect():
            logger.error("Не удалось подключиться к RabbitMQ")
            return

        try:
            # Создаем очередь для ответов пользователю
            user_queue_name = f"user_responses_{user_id}"
            user_queue = await self.channel.declare_queue(
                user_queue_name, durable=True, auto_delete=True
            )

            # Привязываем очередь к обмену с ключом маршрутизации (routing key) user_id
            await user_queue.bind(self.response_exchange, routing_key=str(user_id))

            # Функция для обработки сообщений
            async def process_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        # Получаем данные из сообщения
                        data = json.loads(message.body.decode())
                        logger.info(f"Получен ответ от AI: {data}")

                        # Вызываем callback функцию с данными
                        await callback(data)

                    except json.JSONDecodeError:
                        logger.error(f"Ошибка декодирования JSON: {message.body}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки ответа: {str(e)}")

            # Начинаем прослушивание очереди
            await user_queue.consume(process_message)
            logger.info(f"Начато прослушивание ответов для пользователя {user_id}")

            # Продолжаем бесконечно, пока задача не будет отменена
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"Прослушивание ответов для пользователя {user_id} отменено")
            raise
        except Exception as e:
            logger.error(f"Ошибка при настройке прослушивания ответов: {str(e)}")

    async def publish_response(self, user_id: int, message: Dict[str, Any]):
        """
        Публикация ответа для пользователя через RabbitMQ

        :param user_id: ID пользователя
        :param message: Сообщение с ответом
        """
        # Извлекаем данные из сообщения
        message_id = message.get("message_id", "")
        content = message.get("content", "")

        # Отправляем ответ через RabbitMQ
        await self.send_ai_response(user_id, message_id, content)

    async def start_ai_worker(self, process_message: Callable[[dict[str, Any]], Any]):
        """
        Запуск обработчика запросов к AI

        :param process_message: Функция обработки сообщений
        """
        if not await self.connect():
            logger.error("Не удалось подключиться к RabbitMQ")
            return

        try:
            self.processing = True

            # Функция для обработки сообщений из очереди запросов
            async def on_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        # Получаем данные из сообщения
                        data = json.loads(message.body.decode())
                        logger.info(f"Получен запрос к AI: {data}")

                        # Вызываем callback функцию с данными
                        await process_message(data)

                    except json.JSONDecodeError:
                        logger.error(f"Ошибка декодирования JSON: {message.body}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки запроса: {str(e)}")

            # Начинаем прослушивание очереди запросов
            await self.ai_request_queue.consume(on_message)
            logger.info("AI Worker запущен")

            # Продолжаем, пока не будет остановлено
            try:
                while self.processing:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info("AI Worker остановлен принудительно")
                raise

        except Exception as e:
            logger.error(f"Ошибка при запуске AI Worker: {str(e)}")
        finally:
            self.processing = False

    async def stop_processing(self):
        """
        Остановка обработки сообщений
        """
        self.processing = False
        logger.info("Запрошена остановка обработки очереди сообщений")

    async def send_ai_response(
        self, user_id: int, message_id: str, content: str
    ) -> bool:
        """
        Отправка ответа от AI через RabbitMQ

        :param user_id: ID пользователя
        :param message_id: ID сообщения
        :param content: Содержимое ответа
        :return: Успешность отправки
        """
        if not await self.connect():
            logger.error("Не удалось подключиться к RabbitMQ")
            return False

        try:
            # Формируем данные для ответа
            data = {
                "user_id": user_id,
                "message_id": message_id,
                "content": content,
                "type": "ai_response",  # Добавляем тип сообщения для совместимости
            }

            # Создаем сообщение
            message_body = json.dumps(data).encode()
            rabbit_message = Message(body=message_body, content_type="application/json")

            # Отправляем сообщение в обмен с указанием routing_key = user_id
            await self.response_exchange.publish(
                rabbit_message, routing_key=str(user_id)
            )

            logger.info(
                f"Ответ от AI отправлен, пользователь: {user_id}, ID сообщения: {message_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки ответа от AI: {str(e)}")
            return False

    # Метод для совместимости с предыдущей версией
    async def start_processing(self, process_message: Callable):
        """
        Запуск обработки сообщений из очереди - обертка для start_ai_worker

        :param process_message: Функция обработки сообщения
        """
        await self.start_ai_worker(process_message)
