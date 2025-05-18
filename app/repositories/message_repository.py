from datetime import datetime

from lawly_db.db_models import Message
from lawly_db.db_models.enum_models import ChatTypeEnum, MessageSenderTypeEnum, MessageStatusEnum
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base_repository import BaseRepository


class MessageRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_message_by_id(self, message_id: int) -> Message | None:
        """
        Получение сообщения по ID
        
        :param message_id: ID сообщения
        :return: Объект сообщения или None, если не найден
        """
        query = select(Message).where(Message.id == message_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_ai_messages(
        self, 
        user_id: int, 
        from_date: datetime | None = None, 
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Message], int]:
        """
        Получение сообщений из чата с AI
        
        :param user_id: ID пользователя
        :param from_date: Начальная дата (опционально)
        :param to_date: Конечная дата (опционально)
        :param limit: Лимит сообщений
        :param offset: Смещение для пагинации
        :return: Список сообщений и общее количество
        """
        query = select(Message).where(
            Message.user_id == user_id,
            Message.chat_type == ChatTypeEnum.AI
        )
        
        if from_date:
            query = query.where(Message.created_at >= from_date)
        if to_date:
            query = query.where(Message.created_at <= to_date)
            
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        messages = result.scalars().all()
        
        return list(messages), total
    
    async def get_lawyer_messages(
        self, 
        user_id: int, 
        from_date: datetime | None = None, 
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Message], int]:
        """
        Получение сообщений из чата с юристом
        
        :param user_id: ID пользователя
        :param from_date: Начальная дата (опционально)
        :param to_date: Конечная дата (опционально)
        :param limit: Лимит сообщений
        :param offset: Смещение для пагинации
        :return: Список сообщений и общее количество
        """
        query = select(Message).where(
            Message.user_id == user_id,
            Message.chat_type == ChatTypeEnum.LAWYER
        )
        
        if from_date:
            query = query.where(Message.created_at >= from_date)
        if to_date:
            query = query.where(Message.created_at <= to_date)
            
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        messages = result.scalars().all()
        
        return list(messages), total
    
    async def create_user_ai_message(self, user_id: int, content: str) -> Message:
        """
        Создание сообщения пользователя в чате с AI
        
        :param user_id: ID пользователя
        :param content: Текст сообщения
        :return: Созданное сообщение
        """
        message = Message(
            user_id=user_id,
            chat_type=ChatTypeEnum.AI,
            sender_type=MessageSenderTypeEnum.USER,
            text=content,
            status=MessageStatusEnum.SENT
        )
        
        await self.save(message, self.session)
        return message
    
    async def create_ai_response_message(self, user_id: int, content: str) -> Message:
        """
        Создание ответного сообщения от AI
        
        :param user_id: ID пользователя
        :param content: Текст сообщения
        :return: Созданное сообщение
        """
        message = Message(
            user_id=user_id,
            chat_type=ChatTypeEnum.AI,
            sender_type=MessageSenderTypeEnum.AI,
            text=content,
            status=MessageStatusEnum.SENT
        )
        
        await self.save(message, self.session)
        return message
    
    async def create_user_lawyer_message(self, user_id: int, content: str, document_url: str) -> Message:
        """
        Создание сообщения юриста для пользователя
        
        :param user_id: ID пользователя
        :param content: Текст сообщения
        :param document_url: URL документа
        :return: Созданное сообщение
        """
        message = Message(
            user_id=user_id,
            chat_type=ChatTypeEnum.LAWYER,
            sender_type=MessageSenderTypeEnum.USER,
            document_url=document_url,
            text=content,
            status=MessageStatusEnum.SENT
        )
        
        await self.save(message, self.session)
        return message
    
    async def create_lawyer_response_message(self, user_id: int, lawyer_id: int, content: str) -> Message:
        """
        Создание ответного сообщения от юриста
        
        :param user_id: ID пользователя
        :param lawyer_id: ID юриста
        :param content: Текст сообщения
        :return: Созданное сообщение
        """
        message = Message(
            user_id=user_id,
            chat_type=ChatTypeEnum.LAWYER,
            sender_type=MessageSenderTypeEnum.LAWYER,
            sender_id=lawyer_id,
            text=content,
            status=MessageStatusEnum.SENT
        )
        
        await self.save(message, self.session)
        return message
    
    async def update_message_status(self, message_id: int, status: MessageStatusEnum) -> bool:
        """
        Обновление статуса сообщения
        
        :param message_id: ID сообщения
        :param status: Новый статус
        :return: Успешность обновления
        """
        query = select(Message).where(Message.id == message_id)
        result = await self.session.execute(query)
        message = result.scalar_one_or_none()
        
        if not message:
            return False
        
        message.status = status
        if status == MessageStatusEnum.READ:
            message.read_at = datetime.now()
            
        await self.session.commit()
        return True
