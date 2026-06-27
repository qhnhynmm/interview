import asyncio
import logging
import sys

from app.config import get_settings
from app.infra.tracing import init_tracing, shutdown_tracing

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    settings = get_settings()
    logger.info(
        "Interview worker starting (agent=%s, livekit=%s)",
        settings.agent_name,
        settings.livekit_url,
    )
    try:
        import livekit.agents  # noqa: F401
    except ImportError:
        logger.error(
            "livekit-agents not installed. "
            "Install optional deps: pip install livekit-agents livekit-plugins-openai"
        )
        sys.exit(1)

    # TODO: register LiveKit agent entrypoint using VoicePipeline + MCP client
    logger.info("Worker scaffold ready — implement LiveKit AgentSession in voice_pipeline.py")
    await asyncio.Event().wait()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    init_tracing(service_name=f"{settings.app_name}-worker")
    try:
        asyncio.run(run_worker())
    finally:
        shutdown_tracing()