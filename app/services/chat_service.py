import logging
from collections.abc import Sequence
from datetime import datetime
from typing import List, Optional, Tuple

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
        offset: int = 0
    ) -> Tuple[Sequence[Message], int]:
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
            offset=offset
        )

    async def send_ai_message(self, user_id: int, content: str) -> bool:
        """
        Отправка сообщения AI и получение ответа

        :param user_id: ID пользователя
        :param content: Текст сообщения
        :return: Отправленное сообщение и ответ AI
        """
        # Создаем сообщение пользователя
        user_message = await self.message_repo.create_user_ai_message(
            user_id=user_id,
            content=content
        )

        # Инициализируем сервис очереди и AI клиент
        from services.message_queue_service import MessageQueueService

        message_queue = MessageQueueService()

        try:
            await message_queue.add_message_to_queue(
                user_id=user_id,
                message=content,
                message_id=str(user_message.id)
            )
        except Exception as e:
            logger.error(e)
            return False

        return True

    async def get_lawyer_messages(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Message], int]:
        """
        Получение сообщений из чата с юристом
        
        :param user_id: ID пользователя
        :param from_date: Начальная дата (опционально)
        :param to_date: Конечная дата (опционально)
        :param limit: Лимит сообщений
        :param offset: Смещение для пагинации
        :return: Список сообщений и общее количество
        """
        return await self.message_repo.get_lawyer_messages(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )
