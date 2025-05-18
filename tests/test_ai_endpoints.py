import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from httpx import AsyncClient
from pytest_mock import MockerFixture

from tests.dto import UserDTO, MessageDTO


@pytest.mark.asyncio
async def test_get_ai_messages(ac: AsyncClient, user_dto: UserDTO, message_dto: MessageDTO):
    """Тест GET эндпоинта получения сообщений из чата с AI"""
    # Отправляем запрос
    response = await ac.get(
        "/api/v1/chat/ai/messages",
        headers={"Authorization": f"Bearer {user_dto.token}"}
    )
    
    # Проверяем результат
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем структуру ответа
    assert "total" in data
    assert "has_more" in data
    assert "messages" in data
    assert isinstance(data["messages"], list)
    
    # Проверяем, что в ответе есть наши тестовые сообщения
    message_ids = [msg["id"] for msg in data["messages"]]
    assert message_dto.user_message.id in message_ids
    assert message_dto.ai_message.id in message_ids
    
    # Проверяем поля сообщений
    for msg in data["messages"]:
        assert "id" in msg
        assert "sender_type" in msg
        assert "content" in msg
        assert "created_at" in msg
        assert "status" in msg


@pytest.mark.asyncio
async def test_get_ai_messages_with_date_filter(ac: AsyncClient, user_dto: UserDTO, message_dto: MessageDTO):
    """Тест GET эндпоинта получения сообщений из чата с AI с фильтрацией по датам"""
    # Получаем текущую дату и даты на день раньше/позже
    now = datetime.now()  # Без timezone
    from_date = (now - timedelta(days=1)).isoformat()
    to_date = (now + timedelta(days=1)).isoformat()
    
    # Отправляем запрос с фильтрацией по датам
    response = await ac.get(
        "/api/v1/chat/ai/messages",
        headers={"Authorization": f"Bearer {user_dto.token}"},
        params={"from_date": from_date, "to_date": to_date}
    )
    
    # Проверяем результат
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что есть сообщения в указанном диапазоне дат
    assert len(data["messages"]) > 0


@pytest.mark.asyncio
async def test_get_ai_messages_with_pagination(ac: AsyncClient, user_dto: UserDTO):
    """Тест GET эндпоинта получения сообщений из чата с AI с пагинацией"""
    # Отправляем запрос с пагинацией
    response = await ac.get(
        "/api/v1/chat/ai/messages",
        headers={"Authorization": f"Bearer {user_dto.token}"},
        params={"limit": 1, "offset": 0}
    )
    
    # Проверяем результат
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что вернулось не более limit сообщений
    assert len(data["messages"]) <= 1
    
    # Если есть больше сообщений, проверяем флаг has_more
    if data["total"] > 1:
        assert data["has_more"] is True


@pytest.mark.asyncio
async def test_get_ai_messages_empty(ac: AsyncClient, user_dto: UserDTO):
    """Тест GET эндпоинта получения сообщений из чата с AI без сообщений"""
    # Используем фильтр по датам, который не должен вернуть сообщений
    old_date = (datetime.now() - timedelta(days=30)).isoformat()
    older_date = (datetime.now() - timedelta(days=31)).isoformat()
    
    # Отправляем запрос
    response = await ac.get(
        "/api/v1/chat/ai/messages",
        headers={"Authorization": f"Bearer {user_dto.token}"},
        params={"from_date": older_date, "to_date": old_date}
    )
    
    # Проверяем результат
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что нет сообщений
    assert len(data["messages"]) == 0
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_ai_messages_unauthorized(ac: AsyncClient):
    """Тест GET эндпоинта получения сообщений из чата с AI без авторизации"""
    # Отправляем запрос без токена
    response = await ac.get("/api/v1/chat/ai/messages")
    
    # Проверяем, что доступ запрещен
    assert response.status_code == 401
