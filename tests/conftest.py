import string
import uuid

from datetime import datetime, UTC, timedelta
from typing import AsyncGenerator
from os import getenv as env

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from lawly_db.db_models import User, RefreshSession, Lawyer, LawyerRequest
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from lawly_db.db_models.db_session import get_session, Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

import random
import time
import jwt

from app.repositories.message_repository import MessageRepository
from app.main import app
from app.config import settings

from tests.dto import UserDTO, MessageDTO, LawyerDTO, LawyerRequestDTO


time.sleep(2)

# DATABASE
DATABASE_URL_TEST = (
    f'postgresql+asyncpg://{env("test_db_login")}:{env("test_db_password")}'
    f'@{env("test_db_host")}:{env("test_db_port")}/{env("test_db_name")}'
)

engine_test = create_async_engine(DATABASE_URL_TEST, poolclass=NullPool)

async_session_maker = async_sessionmaker(engine_test, expire_on_commit=False)

Base.metadata.bind = engine_test


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_session] = override_get_async_session


@pytest.fixture(autouse=True, scope='session')
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


client = TestClient(app)


@pytest.fixture(scope="session")
async def ac() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def generate_test_token(user_id: int) -> str:
    """
    Генерирует тестовый JWT токен
    
    :param user_id: ID пользователя
    :return: JWT токен
    """
    payload = {
        "user_id": user_id,
        "expires": time.time() + 86400  # 24 часа
    }
    token = jwt.encode(
        payload,
        settings.jwt_settings.secret_key,
        algorithm=settings.jwt_settings.algorithm,
    )
    return token


@pytest.fixture(scope="function")
async def user_dto() -> AsyncGenerator[UserDTO, None]:
    async with async_session_maker() as session:
        # Создаем тестового пользователя
        user = User(
            email="".join(
                [random.choice(string.ascii_letters + string.digits) for _ in range(5)]
            )
            + "@gmail.com",
            password="hashed_password",  # В реальных тестах это был бы хэш
            name="Тестовый Пользователь",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Создаем refresh session для пользователя
        expires_at = (
            datetime.now(UTC)
            + timedelta(minutes=settings.jwt_settings.refresh_token_expire_minutes)
        ).timestamp()
        refresh_session = RefreshSession(
            user_id=user.id,
            refresh_token=uuid.uuid4(),
            ip="78.123.321.121",
            device_os="android 13",
            device_name="samsung s23",
            device_id="4965483F-2297-4FAF-AD26-D6F2BA888684",
            expires_in=int(expires_at),
        )
        session.add(refresh_session)
        await session.commit()
        
        # Генерируем токен для тестов
        token = generate_test_token(user.id)
        
        yield UserDTO(user=user, refresh_session=refresh_session, token=token, session=session)
        
        # Очистка после тестов
        await session.delete(user)
        await session.commit()


@pytest.fixture(scope="function")
async def message_dto(user_dto: UserDTO) -> AsyncGenerator[MessageDTO, None]:
    async with async_session_maker() as session:
        message_repo = MessageRepository(session)
        
        # Создаем тестовое сообщение от пользователя
        user_message = await message_repo.create_user_ai_message(
            user_id=user_dto.user.id,
            content="Тестовое сообщение"
        )
        
        # Создаем тестовый ответ от AI
        ai_message = await message_repo.create_ai_response_message(
            user_id=user_dto.user.id,
            content="Ответ на тестовое сообщение"
        )
        
        yield MessageDTO(
            user_message=user_message,
            ai_message=ai_message,
            session=session
        )


@pytest.fixture(scope="function")
async def lawyer_dto(session: AsyncSession) -> AsyncGenerator[LawyerDTO, None]:
    # Создаем тестового пользователя-юриста
    user = User(
        email="".join(
            [random.choice(string.ascii_letters + string.digits) for _ in range(5)]
        )
        + "@lawyer.com",
        password="hashed_password",
        name="Тестовый Юрист",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Создаем запись юриста
    lawyer = Lawyer(
        user_id=user.id
    )
    session.add(lawyer)
    await session.commit()
    await session.refresh(lawyer)

    # Генерируем токен для тестов
    token = generate_test_token(user.id)

    yield LawyerDTO(user=user, lawyer=lawyer, token=token)

    # Очистка после тестов
    await session.delete(lawyer)
    await session.delete(user)
    await session.commit()


@pytest.fixture(scope="function")
async def lawyer_request_dto(user_dto: UserDTO, lawyer_dto: LawyerDTO,
                             session: AsyncSession) -> AsyncGenerator[LawyerRequestDTO, None]:
    # Создаем тестовую заявку юриста
    lawyer_request = LawyerRequest(
        user_id=user_dto.user.id,
        lawyer_id=lawyer_dto.lawyer.id,
        status=LawyerRequestStatusEnum.PENDING,
        note="Тестовая заявка юристу",
        document_url="https://example.com/test-document.pdf"  # Добавляем документ_url, т.к. он не может быть null
    )
    session.add(lawyer_request)
    await session.commit()
    await session.refresh(lawyer_request)

    yield LawyerRequestDTO(
        user=user_dto.user,
        lawyer=lawyer_dto.lawyer,
        request=lawyer_request,
        user_token=user_dto.token,
        lawyer_token=lawyer_dto.token,
        session=session
    )

    # Очистка после тестов
    await session.delete(lawyer_request)
    await session.commit()
