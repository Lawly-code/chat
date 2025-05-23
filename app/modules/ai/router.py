from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth.auth_bearer import JWTBearer, JWTHeader
from modules.ai.descriptions import (
    get_ai_messages_description,
)
from modules.ai.dto import MessageResponseDTO, MessagesResponseDTO
from modules.ai.response import get_ai_messages_response
from services.chat_service import ChatService

router = APIRouter(tags=["AI-помощник"])


@router.get(
    "/messages",
    summary="Получение сообщений из чата с AI",
    description=get_ai_messages_description,
    responses=get_ai_messages_response,
    response_model=MessagesResponseDTO,
)
async def get_messages(
    from_date: Optional[datetime] = Query(
        None, description="Начальная дата для выборки сообщений (включительно)"
    ),
    to_date: Optional[datetime] = Query(
        None, description="Конечная дата для выборки сообщений (включительно)"
    ),
    limit: int = Query(50, description="Максимальное количество сообщений"),
    offset: int = Query(0, description="Смещение для пагинации"),
    token: JWTHeader = Depends(JWTBearer()),
    chat_service: ChatService = Depends(),
):
    messages, total = await chat_service.get_ai_messages(
        user_id=token.user_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    # Преобразуем сообщения в DTO
    message_dtos = []
    for msg in messages:
        message_dtos.append(
            MessageResponseDTO(
                id=msg.id,
                sender_type=msg.sender_type.value,
                sender_id=msg.sender_id if msg.sender_id else None,
                content=msg.text,
                created_at=msg.created_at,
                status=msg.status.value,
            )
        )

    return MessagesResponseDTO(
        total=total, has_more=total > offset + limit, messages=message_dtos
    )
