from fastapi import APIRouter
from modules import ai, lawyer

router = APIRouter()

router.include_router(ai.router, prefix="/ai")
router.include_router(lawyer.router, prefix="/lawyer")
