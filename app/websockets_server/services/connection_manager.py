import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

from websockets_server.dto import WebSocketBaseMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Менеджер WebSocket соединений
    """

    def __init__(self):
        # Активные соединения в формате {user_id: [connection1, connection2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Установка нового соединения
        
        :param websocket: WebSocket соединение
        :param user_id: ID пользователя
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"Новое WebSocket соединение для пользователя {user_id}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """
        Закрытие соединения
        
        :param websocket: WebSocket соединение
        :param user_id: ID пользователя
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            # Если это последнее соединение пользователя, удаляем запись
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket соединение закрыто для пользователя {user_id}")

    async def send_message(self, message: WebSocketBaseMessage, user_id: int):
        """
        Отправка сообщения пользователю
        
        :param message: Сообщение для отправки
        :param user_id: ID пользователя
        """
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message.dict())
                    logger.info(f"Сообщение типа {message.type} отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения: {str(e)}")
                    disconnected.append(connection)
            
            # Удаляем разорванные соединения
            for connection in disconnected:
                if connection in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(connection)
            
            # Если это было последнее соединение пользователя, удаляем запись
            if user_id in self.active_connections and not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
    async def broadcast(self, message: WebSocketBaseMessage):
        """
        Отправка сообщения всем подключенным пользователям
        
        :param message: Сообщение для отправки
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_message(message, user_id)
