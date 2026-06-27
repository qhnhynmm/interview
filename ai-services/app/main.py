import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.mcp.server import router as mcp_router

settings = get_settings()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_prefix)
    application.include_router(mcp_router)

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "llm_enabled": settings.llm_enabled,
        }

    return application


app = create_app()