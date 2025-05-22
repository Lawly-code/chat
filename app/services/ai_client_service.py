import logging
from protos.ai_service.client import AIAssistantClient
from protos.ai_service.dto import AIRequestDTO

from config import settings

logger = logging.getLogger(__name__)


class AIClientService:
    """
    Сервис для взаимодействия с AI через gRPC
    """

    def __init__(self):
        # Инициализация с указанными параметрами (хост ai_grpc_service и порт 50051)
        self.client = AIAssistantClient(
            host=settings.ai_service.host, port=settings.ai_service.port
        )
        self.connected = False

    async def connect(self):
        """
        Подключение к gRPC серверу
        """
        if not self.connected:
            try:
                await self.client.connect()
                self.connected = True
                logger.info("Подключение к AI gRPC серверу установлено")
            except Exception as e:
                logger.error(f"Ошибка подключения к AI gRPC серверу: {str(e)}")
                raise

    async def send_message(self, message: str) -> str:
        """
        Отправка сообщения AI и получение ответа

        :param message: Текст сообщения
        :return: Ответ AI
        """
        try:
            # Подключаемся к gRPC серверу, если еще не подключены
            if not self.connected:
                await self.connect()

            # Создаем DTO для запроса
            request = AIRequestDTO(
                user_prompt=message,
                temperature=0.7,  # Значение по умолчанию, можно настроить
                max_tokens=2000,  # Значение по умолчанию, можно настроить
            )

            # Отправляем запрос и получаем ответ
            logger.info(f"Отправка запроса к AI: {message[:50]}...")
            response = await self.client.ai_chat(request)

            # Проверяем ответ
            if response:
                logger.info(f"Получен ответ от AI: {response.assistant_reply[:50]}...")
                return response.assistant_reply
            else:
                error_message = "AI не вернул ответ"
                logger.error(error_message)
                return (
                    f"Извините, произошла ошибка при обработке запроса: {error_message}"
                )

        except Exception as e:
            logger.error(f"Ошибка при отправке запроса к AI: {str(e)}")
            # Пробуем переподключиться при ошибке
            self.connected = False

            # Возвращаем сообщение об ошибке
            return f"Произошла ошибка: {str(e)}"

        finally:
            # Не закрываем соединение после каждого запроса для улучшения производительности
            # Если нужно закрыть соединение, используйте:
            # await self.client.close()
            pass

    async def close(self):
        """
        Закрытие соединения с gRPC сервером
        """
        if self.connected:
            try:
                await self.client.close()
                self.connected = False
                logger.info("Соединение с AI gRPC сервером закрыто")
            except Exception as e:
                logger.error(
                    f"Ошибка при закрытии соединения с AI gRPC сервером: {str(e)}"
                )
