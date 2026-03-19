from fastapi import APIRouter

from app.api.v1.rewrite import router as rewrite_router
from app.api.v1.youtube import router as youtube_router

api_router = APIRouter()
api_router.include_router(rewrite_router, prefix="/v1", tags=["rewrite"])
api_router.include_router(youtube_router, prefix="/v1", tags=["youtube"])
