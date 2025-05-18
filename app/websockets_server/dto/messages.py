from typing import Optional

from pydantic import BaseModel


class WebSocketBaseMessage(BaseModel):
    """Базовый класс для всех WebSocket сообщений"""

    type: str


class ConnectionStatusMessage(WebSocketBaseMessage):
    """Сообщение о статусе подключения"""

    type: str = "connection_status"
    status: str
    user_id: int


class UserMessage(WebSocketBaseMessage):
    """Сообщение от пользователя к AI"""

    type: str = "user_message"
    content: str


class MessageReceivedConfirmation(WebSocketBaseMessage):
    """Подтверждение получения сообщения"""

    type: str = "message_received"
    message_id: str
    status: str = "processing"


class AIResponseMessage(WebSocketBaseMessage):
    """Ответ от AI"""

    type: str = "ai_response"
    message_id: str
    user_id: int
    content: str


class ErrorMessage(WebSocketBaseMessage):
    """Сообщение об ошибке"""

    type: str = "error"
    message: str
    error_code: Optional[str] = None


# Для RabbitMQ
class RabbitMQAIRequest(BaseModel):
    """Запрос к AI через RabbitMQ"""

    user_id: int
    message: str
    message_id: str


class RabbitMQAIResponse(BaseModel):
    """Ответ от AI через RabbitMQ"""

    user_id: int
    message_id: str
    content: str
