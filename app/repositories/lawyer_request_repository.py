from typing import Optional

from lawly_db.db_models import LawyerRequest
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_repository import BaseRepository


class LawyerRequestRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_lawyer_request(
        self, user_id: int, message: str, document_url: Optional[str] = None
    ) -> LawyerRequest:
        """
        Создание запроса на консультацию к юристу
        
        :param user_id: ID пользователя
        :param message: Текст сообщения
        :param document_url: URL документа (опционально)
        :return: Созданный запрос
        """
        lawyer_request = LawyerRequest(
            user_id=user_id,
            message=message,
            document_url=document_url,
            status=LawyerRequestStatusEnum.PENDING
        )
        
        await self.save(lawyer_request, self.session)
        return lawyer_request
    
    async def get_user_lawyer_request(self, user_id: int, request_id: int) -> Optional[LawyerRequest]:
        """
        Получение запроса на консультацию
        
        :param user_id: ID пользователя
        :param request_id: ID запроса
        :return: Запрос или None, если не найден
        """
        query = select(LawyerRequest).where(
            LawyerRequest.user_id == user_id,
            LawyerRequest.id == request_id
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
