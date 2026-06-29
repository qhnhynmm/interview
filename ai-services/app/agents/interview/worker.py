import logging
import sys

from livekit.agents import WorkerOptions, cli

from app.agents.interview.voice_pipeline import entrypoint
from app.config import get_settings
from app.infra.tracing import init_tracing, shutdown_tracing

logger = logging.getLogger(__name__)


def run_worker() -> None:
    settings = get_settings()
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        logger.error(
            "LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required for the interview worker"
        )
        sys.exit(1)
    if not settings.gemini_api_key.strip():
        logger.error("GEMINI_API_KEY is required for Gemini Live voice agent")
        sys.exit(1)

    logger.info(
        "Interview worker starting (agent=%s, livekit=%s)",
        settings.agent_name,
        settings.livekit_url,
    )

    try:
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint,
                agent_name=settings.agent_name,
                ws_url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
                port=settings.livekit_worker_port,
            )
        )
    finally:
        shutdown_tracing()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    init_tracing(service_name=f"{settings.app_name}-worker")
    run_worker()