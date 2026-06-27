"""LiveKit voice pipeline — STT → LLM → TTS. Not MAF-based."""

import logging

from app.agents.interview.session import InterviewSession
from app.config import get_settings

logger = logging.getLogger(__name__)


class VoicePipeline:
    def __init__(self, session: InterviewSession) -> None:
        self.session = session
        self._settings = get_settings()

    async def start(self) -> None:
        logger.info(
            "Voice pipeline ready for %s (livekit=%s, mcp=%s)",
            self.session.interview_id,
            self._settings.livekit_url,
            self._settings.mcp_sse_url,
        )
        # TODO: connect LiveKit room, wire STT/TTS adapters, consume MCP tools