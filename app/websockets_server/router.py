from fastapi import APIRouter, Depends, WebSocket, Query
from sqlalchemy.ext.asyncio import AsyncSession

from lawly_db.db_models.db_session import get_session
from .handlers.websocket_handler import websocket_endpoint

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """
    WebSocket эндпоинт для взаимодействия с AI в реальном времени

    :param websocket: WebSocket соединение
    :param token: JWT токен для аутентификации
    :param session: Сессия базы данных
    """
    await websocket_endpoint(websocket, token, session)
