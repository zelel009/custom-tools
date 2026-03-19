from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.db import init_db

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Feature 2 + 3 API: Rewrite content & extract YouTube content",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    Path(settings.export_dir).mkdir(parents=True, exist_ok=True)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "env": settings.app_env}


app.include_router(api_router, prefix="/api")
