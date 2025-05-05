import json
import asyncio
import logging
from typing import Callable, Dict, Any
import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)


class MessageQueueService:
    """
    Сервис для работы с очередью сообщений через Redis
    """

    def __init__(self):
        self.redis_url = settings.redis_settings.url
        self.redis = None
        self.queue_name = "ai_message_queue"
        self.processing = False

    async def connect(self):
        """
        Установка соединения с Redis
        """
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)
            logger.info("Соединение с Redis установлено")

    async def disconnect(self):
        """
        Закрытие соединения с Redis
        """
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Соединение с Redis закрыто")

    async def add_message_to_queue(self, user_id: int, message: str, message_id: str) -> bool:
        """
        Добавление сообщения в очередь
        
        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param message_id: ID сообщения
        :return: Успешность добавления
        """
        await self.connect()
        
        # Формируем данные для очереди
        queue_item = {
            "user_id": user_id,
            "message": message,
            "message_id": message_id
        }
        
        try:
            # Добавляем в очередь
            await self.redis.lpush(self.queue_name, json.dumps(queue_item))
            logger.info(f"Сообщение {message_id} добавлено в очередь")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления сообщения в очередь: {str(e)}")
            return False

    async def publish_response(self, user_id: int, message: Dict[str, Any]):
        """
        Публикация ответа для WebSocket - использует Redis список вместо PubSub
        
        :param user_id: ID пользователя
        :param message: Сообщение для отправки
        """
        await self.connect()
        
        try:
            # Ключ для хранения ответов для пользователя
            response_key = f"user_responses:{user_id}"
            
            # Сериализуем сообщение в JSON и добавляем в список ответов
            await self.redis.rpush(response_key, json.dumps(message))
            
            # Устанавливаем TTL для ключа (например, 1 час), чтобы избежать утечки памяти
            await self.redis.expire(response_key, 3600)
            
            logger.info(f"Ответ сохранен для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка публикации ответа: {str(e)}")

    async def start_processing(self, process_message: Callable):
        """
        Запуск обработки сообщений из очереди
        
        :param process_message: Функция обработки сообщения
        """
        if self.processing:
            return
            
        self.processing = True
        await self.connect()
        
        logger.info("Запущена обработка очереди сообщений")
        
        try:
            while self.processing:
                # Получаем сообщение из очереди с таймаутом
                result = await self.redis.brpop(self.queue_name, timeout=1)
                
                if result:
                    _, message_data = result
                    try:
                        # Парсим JSON
                        message_item = json.loads(message_data)
                        # Обрабатываем сообщение
                        await process_message(message_item)
                    except json.JSONDecodeError:
                        logger.error(f"Ошибка декодирования JSON: {message_data}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки сообщения: {str(e)}")
                        
                # Небольшая пауза для снижения нагрузки
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Ошибка в цикле обработки сообщений: {str(e)}")
        finally:
            self.processing = False
            logger.info("Обработка очереди сообщений остановлена")

    async def stop_processing(self):
        """
        Остановка обработки сообщений
        """
        self.processing = False
        logger.info("Запрошена остановка обработки очереди сообщений")
