from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, Response

from api.auth.auth_bearer import JWTBearer, JWTHeader
from modules.ai.descriptions import get_ai_messages_description, send_ai_message_description
from modules.ai.dto import MessageRequestDTO, MessageResponseDTO, MessagesResponseDTO
from modules.ai.response import get_ai_messages_response, send_ai_message_response
from services.chat_service import ChatService

router = APIRouter(tags=["AI-помощник"])


@router.get(
    "/messages",
    summary="Получение сообщений из чата с AI",
    description=get_ai_messages_description,
    responses=get_ai_messages_response,
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
    messages, total = await chat_service.get_ai_messages(
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
                sender_name=None,
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
    "/messages",
    summary="Отправка сообщения AI-помощнику",
    description=send_ai_message_description,
    responses=send_ai_message_response,
    response_class=Response,
    status_code=status.HTTP_202_ACCEPTED
)
async def send_message(
    message_request: MessageRequestDTO,
    token: JWTHeader = Depends(JWTBearer()),
    chat_service: ChatService = Depends()
):
    resp = await chat_service.send_ai_message(
        user_id=token.user_id,
        content=message_request.content
    )

    if resp:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return Response(status_code=status.HTTP_400_BAD_REQUEST)