import asyncio
from contextlib import asynccontextmanager

from api import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lawly_db.db_models.db_session import global_init

from websockets_server.router import router as websocket_router
from websockets_server.workers.ai_worker import AIWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД
    await global_init()
    
    # Создаем и запускаем AI воркер
    ai_worker = AIWorker()
    worker_task = asyncio.create_task(ai_worker.start())
    
    yield
    
    # Останавливаем AI воркер
    await ai_worker.stop()
    
    # Ждем завершения задачи
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Lawly Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем REST API роутеры
app.include_router(router, prefix="/api/v1/chat")

# Подключаем WebSocket роутер
app.include_router(websocket_router)
