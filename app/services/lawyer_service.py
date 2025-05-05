from typing import Optional

from fastapi import Depends
from lawly_db.db_models import LawyerRequest, Message
from lawly_db.db_models.db_session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.lawyer_request_repository import LawyerRequestRepository
from repositories.message_repository import MessageRepository


class LawyerService:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.lawyer_request_repo = LawyerRequestRepository(session)
        self.message_repo = MessageRepository(session)

    async def create_lawyer_request(
        self, user_id: int, message: str, document_url: Optional[str] = None
    ) -> Message:
        """
        Создание обращения к юристу
        
        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param document_url: URL документа (опционально)
        :return: Созданное сообщение
        """
        # Создаем запрос на консультацию
        lawyer_request = await self.lawyer_request_repo.create_lawyer_request(
            user_id=user_id,
            message=message,
            document_url=document_url
        )
        
        # Создаем сообщение пользователя в чате с юристом
        user_message = await self.message_repo.create_user_lawyer_message(
            user_id=user_id,
            content=message
        )
        
        return user_message
