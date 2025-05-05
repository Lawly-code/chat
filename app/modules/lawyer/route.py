from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from api.auth.auth_bearer import JWTBearer, JWTHeader
from modules.lawyer.descriptions import create_lawyer_request_description, get_lawyer_messages_description
from modules.lawyer.dto import LawyerRequestDTO, MessageResponseDTO, MessagesResponseDTO
from modules.lawyer.response import create_lawyer_request_response, get_lawyer_messages_response
from services.chat_service import ChatService
from services.lawyer_service import LawyerService

router = APIRouter(tags=["Юридические консультации"])


@router.get(
    "/messages",
    summary="Получение сообщений из чата с юристом",
    description=get_lawyer_messages_description,
    responses=get_lawyer_messages_response,
    response_model=MessagesResponseDTO
)
async def get_messages(
    from_date: Optional[datetime] = Query(None, description="Начальная дата для выборки сообщений (включительно)"),
    to_date: Optional[datetime] = Query(None, description="Конечная дата для выборки сообщений (включительно)"),
    limit: int = Query(50, description="Максимальное количество сообщений"),
    offset: int = Query(0, description="Смещение для пагинации"),
    token: JWTHeader = Depends(JWTBearer()),
    chat_service: ChatService = Depends()
):
    messages, total = await chat_service.get_lawyer_messages(
        user_id=token.user_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    # Преобразуем сообщения в DTO
    message_dtos = []
    for msg in messages:
        message_dtos.append(
            MessageResponseDTO(
                id=f"msg-{msg.id}",
                sender_type=msg.sender_type.value,
                sender_id=f"sender-{msg.sender_id}" if msg.sender_id else None,
                sender_name=None,  # Предполагается, что имя отправителя берется из другой таблицы по sender_id
                content=msg.text,
                created_at=msg.created_at,
                status=msg.status.value
            )
        )
    
    return MessagesResponseDTO(
        total=total,
        has_more=total > offset + limit,
        messages=message_dtos
    )


@router.post(
    "/request",
    summary="Создание обращения к юристу",
    description=create_lawyer_request_description,
    responses=create_lawyer_request_response,
    response_model=MessageResponseDTO,
    status_code=status.HTTP_201_CREATED
)
async def create_request(
    lawyer_request: LawyerRequestDTO,
    token: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends()
):
    user_message = await lawyer_service.create_lawyer_request(
        user_id=token.user_id,
        message=lawyer_request.message,
        document_url=lawyer_request.document_url.unicode_string() if lawyer_request.document_url else None
    )
    
    return MessageResponseDTO(
        id=f"msg-{user_message.id}",
        sender_type=user_message.sender_type.value,
        sender_id=None,
        sender_name=None,
        content=user_message.text,
        created_at=user_message.created_at,
        status=user_message.status.value
    )
