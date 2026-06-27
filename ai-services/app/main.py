import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.infra.tracing import init_tracing, shutdown_tracing
from app.mcp.server import router as mcp_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    init_tracing(service_name=settings.app_name)
    yield
    shutdown_tracing()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_prefix)
    application.include_router(mcp_router)

    if settings.otel_enabled:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(application)
        except Exception as exc:
            logger.warning("FastAPI tracing instrumentation skipped: %s", exc)

    @application.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "llm_enabled": settings.llm_enabled,
            "llm_provider": settings.effective_llm_provider if settings.llm_enabled else None,
            "otel_enabled": settings.otel_enabled,
            "otel_endpoint": settings.otel_otlp_endpoint if settings.otel_enabled else None,
        }

    return application


app = create_app()