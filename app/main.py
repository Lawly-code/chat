import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lawly_db.db_models.db_session import global_init

from modules import ai, lawyer
from websockets_server.router import router as websocket_router
from websockets_server.workers.ai_worker import AIWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await global_init()

    ai_worker = AIWorker()
    worker_task = asyncio.create_task(ai_worker.start())

    yield

    await ai_worker.stop()

    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Lawly Chat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lawyer.lawly.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем WebSocket роутер
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSockets"])
app.include_router(ai.router, prefix="/api/v1/chat/ai")
app.include_router(lawyer.router, prefix="/api/v1/chat/lawyer")
