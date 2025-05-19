from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# Enum для статуса заявки юриста
class LawyerRequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


# Request models
class LawyerRequestFilterDTO(BaseModel):
    status: LawyerRequestStatus = Field(
        ..., example="pending", description="Статус заявки для фильтрации"
    )


class LawyerRequestUpdateDTO(BaseModel):
    request_id: int = Field(..., example=123, description="ID заявки для обновления")
    status: LawyerRequestStatus = Field(
        ..., example="processing", description="Новый статус заявки"
    )
    document_bytes: list[int] | None = Field(
        None, description="Документ в байтах (необходим для статуса 'completed')"
    )
    description: str | None = Field(
        None,
        example="Работа выполнена",
        description="Описание выполненной работы (необходимо для статуса 'completed')",
    )


class LawyerRequestCreateDTO(BaseModel):
    description: str = Field(
        ...,
        example="Нужно проверить договор купли-продажи",
        description="Описание заявки для юриста",
    )
    document_bytes: list[int] | None = Field(
        None, description="Документ в байтах (опционально)"
    )


# Response models
class LawyerRequestDTO(BaseModel):
    id: int = Field(..., example=123, description="Уникальный ID заявки")
    title: str = Field(
        ..., example="Заявка №123: Проверка документов", description="Заголовок заявки"
    )
    description: str = Field(
        ...,
        example="Нужно проверить комплект документов до 20 мая",
        description="Описание заявки",
    )
    status: LawyerRequestStatus = Field(
        ..., example="pending", description="Текущий статус заявки"
    )
    file_url: str | None = Field(
        None,
        example="https://example.com/sample1.pdf",
        description="URL файла документа",
    )
    created_at: datetime = Field(
        ..., example="2025-05-10T12:00:00Z", description="Дата создания заявки"
    )
    updated_at: datetime = Field(
        ...,
        example="2025-05-10T12:00:00Z",
        description="Дата последнего обновления заявки",
    )


class LawyerRequestsDTO(BaseModel):
    total: int = Field(..., example=10, description="Общее количество заявок")
    requests: list[LawyerRequestDTO] = Field(..., description="Список заявок юриста")


class LawyerResponseDTO(BaseModel):
    message_id: int = Field(..., example=456, description="ID сообщения юриста")
    note: str = Field(
        ..., example="Проверка документов", description="Описание ответа юриста"
    )


class LawyerResponsesDTO(BaseModel):
    total: int = Field(..., example=5, description="Общее количество ответов")
    responses: list[LawyerResponseDTO] = Field(
        ..., description="Список ответов юриста за указанный период"
    )


class LawyerRequestCreateResponseDTO(BaseModel):
    id: int = Field(..., example=123, description="ID созданной заявки")
    status: LawyerRequestStatus = Field(
        ..., example="pending", description="Статус заявки"
    )
    created_at: datetime = Field(
        ..., example="2025-05-10T12:00:00Z", description="Дата создания заявки"
    )


# Request model для получения документа
class DocumentRetrievalByRequestIdDTO(BaseModel):
    lawyer_request_id: int = Field(..., example=123, description="ID заявки юриста")


class DocumentRetrievalByMessageIdDTO(BaseModel):
    message_id: int = Field(..., example=456, description="ID сообщения")
