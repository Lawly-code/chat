from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageRequestDTO(BaseModel):
    content: str = Field(..., example="Как мне составить претензию на возврат товара?")


class MessageResponseDTO(BaseModel):
    id: int = Field(..., example=1234)
    sender_type: str = Field(
        ..., example="user", description="Тип отправителя: user, ai, lawyer"
    )
    sender_id: Optional[int] = Field(
        None, example=123, description="ID отправителя (для юристов)"
    )
    content: str = Field(..., example="Как мне составить претензию на возврат товара?")
    created_at: datetime = Field(..., example="2023-01-15T12:00:00Z")
    status: str = Field(
        ..., example="delivered", description="Статус сообщения: sent, delivered, read"
    )


class MessagesResponseDTO(BaseModel):
    total: int = Field(
        ..., example=45, description="Общее количество сообщений в выбранном диапазоне"
    )
    has_more: bool = Field(
        ..., example=True, description="Флаг наличия дополнительных сообщений"
    )
    messages: List[MessageResponseDTO] = Field(..., description="Список сообщений")
