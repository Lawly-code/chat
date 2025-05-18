import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from fastapi import Depends
from lawly_db.db_models import Message
from lawly_db.db_models.db_session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.message_repository import MessageRepository


logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.message_repo = MessageRepository(session)

    async def get_ai_messages(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Message], int]:
        """
        Получение сообщений из чата с AI

        :param user_id: ID пользователя
        :param from_date: Начальная дата (опционально)
        :param to_date: Конечная дата (опционально)
        :param limit: Лимит сообщений
        :param offset: Смещение для пагинации
        :return: Список сообщений и общее количество
        """
        return await self.message_repo.get_ai_messages(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
