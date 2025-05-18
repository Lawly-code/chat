import logging
from typing import Any

from services.ai_client_service import AIClientService
from repositories.message_repository import MessageRepository
from sqlalchemy.ext.asyncio import AsyncSession
from .rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)


class AIService:
    """
    Сервис для работы с AI
    """
    
    def __init__(self, message_repo: MessageRepository, rabbitmq_service: RabbitMQService):
        self.message_repo = message_repo
        self.rabbitmq_service = rabbitmq_service
        self.ai_client = AIClientService()
        
    async def process_ai_request(self, data: dict[str, Any]):
        """
        Обработка запроса к AI
        
        :param data: Данные запроса (user_id, message, message_id)
        """
        user_id = data.get("user_id")
        message = data.get("message")
        message_id = data.get("message_id")
        
        logger.info(f"Обработка запроса к AI: user_id={user_id}, message_id={message_id}")
        
        try:
            # Получаем ответ от AI
            ai_response = await self.ai_client.send_message(message)
            logger.info(f"Получен ответ от AI для сообщения {message_id}")
            
            # Отправляем ответ через RabbitMQ
            await self.rabbitmq_service.send_ai_response(
                user_id=user_id,
                message_id=message_id,
                content=ai_response
            )
            
            # Сохраняем ответ в базу данных
            async with AsyncSession() as session:
                message_repo = MessageRepository(session)
                await message_repo.create_ai_response_message(
                    user_id=user_id,
                    content=ai_response
                )
                logger.info(f"Ответ AI сохранен в базе данных для пользователя {user_id}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки запроса к AI: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
