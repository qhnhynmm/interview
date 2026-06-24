from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import init_db
from app.services.object_storage import ensure_bucket

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.minio_enabled:
        ensure_bucket(settings.minio_bucket_cvs)
    if not settings.gemini_api_key:
        import logging

        logging.getLogger(__name__).warning(
            "GEMINI_API_KEY is not set — CV PDF/DOCX extraction will use placeholder text"
        )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}