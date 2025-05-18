from datetime import datetime

from lawly_db.db_models import LawyerRequest
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base_repository import BaseRepository


class LawyerRequestRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_lawyer_request(
        self, user_id: int, message: str, document_url: str | None = None
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
            note=message,
            document_url=document_url,
            status=LawyerRequestStatusEnum.PENDING
        )
        
        await self.save(lawyer_request, self.session)
        return lawyer_request
    
    async def get_user_lawyer_request(self, user_id: int, request_id: int) -> LawyerRequest | None:
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
        
    async def get_lawyer_requests_by_status(
        self, lawyer_id: int, status: LawyerRequestStatusEnum
    ) -> tuple[list[LawyerRequest], int]:
        """
        Получение заявок юриста по статусу
        
        :param lawyer_id: ID юриста
        :param status: Фильтр по статусу
        :return: Кортеж из списка объектов LawyerRequest и общего количества
        """
        query = select(LawyerRequest).where(
            LawyerRequest.status == status
        )
        if status == LawyerRequestStatusEnum.COMPLETED:
            query = query.where(LawyerRequest.lawyer_id == lawyer_id)
        
        result = await self.session.execute(query)
        requests = result.scalars().all()
        
        count_query = select(func.count()).select_from(LawyerRequest).where(
            LawyerRequest.status == status
        )
        if status == LawyerRequestStatusEnum.COMPLETED:
            count_query = count_query.where(LawyerRequest.lawyer_id == lawyer_id)

        result = await self.session.execute(count_query)
        total_count = result.scalar_one()
        
        return list(requests), total_count
        
    async def get_lawyer_request_by_id(self, request_id: int) -> LawyerRequest | None:
        """
        Получение заявки юриста по ID
        
        :param request_id: ID заявки
        :return: Объект заявки или None, если не найден
        """
        query = select(LawyerRequest).where(LawyerRequest.id == request_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def update_lawyer_request_status(
        self,
        request_id: int,
        status: LawyerRequestStatusEnum,
        lawyer_id: int | None = None,
        note: str | None = None
    ) -> LawyerRequest | None:
        """
        Обновление статуса заявки юриста
        
        :param request_id: ID заявки
        :param status: Новый статус
        :param lawyer_id: ID юриста (опционально)
        :param document_url: URL документа (опционально)
        :param note: Примечание (опционально)
        :return: Обновленная заявка или None, если не найдена
        """
        request = await self.get_lawyer_request_by_id(request_id)
        if not request:
            return None
            
        request.status = status
        request.updated_at = datetime.now()
            
        if note:
            request.note = note

        if lawyer_id and status == LawyerRequestStatusEnum.PROCESSING:
            request.lawyer_id = lawyer_id
            
        await self.session.commit()
        await self.session.refresh(request)
        
        return request
