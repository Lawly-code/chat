from lawly_db.db_models import RefreshSession, User, Message, Lawyer, LawyerRequest
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class UserDTO:
    """DTO для тестирования с пользователем"""

    user: User
    refresh_session: RefreshSession
    token: str
    session: AsyncSession


@dataclass
class MessageDTO:
    """DTO для тестирования с сообщениями"""

    user_message: Message
    ai_message: Message
    session: AsyncSession


@dataclass
class LawyerDTO:
    """DTO для тестирования с юристом"""

    user: User
    lawyer: Lawyer
    token: str


@dataclass
class LawyerRequestDTO:
    """DTO для тестирования с заявкой юриста"""

    user: User
    lawyer: Lawyer
    request: LawyerRequest
    user_token: str
    lawyer_token: str
    session: AsyncSession
