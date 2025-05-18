from lawly_db.db_models import Lawyer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base_repository import BaseRepository


class LawyerRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_lawyer_by_user_id(self, user_id: int) -> Lawyer | None:
        """
        Получение юриста по ID пользователя

        :param user_id: ID пользователя
        :return: Объект юриста или None, если не найден
        """
        query = select(Lawyer).where(Lawyer.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def check_is_lawyer(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь юристом

        :param user_id: ID пользователя для проверки
        :return: True если пользователь юрист, False в противном случае
        """
        lawyer = await self.get_lawyer_by_user_id(user_id)
        return lawyer is not None
