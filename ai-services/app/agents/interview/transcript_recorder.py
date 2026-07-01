"""Persist spoken turns to backend transcript via MCP append_transcript_turn."""

from __future__ import annotations

import asyncio
import logging
import time

from livekit.agents import AgentSession
from livekit.agents.llm import ChatMessage
from livekit.agents.voice.events import ConversationItemAddedEvent

from app.agents.interview.mcp_client import MCPClient

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "user": "candidate",
    "assistant": "agent",
}


class TranscriptRecorder:
    """Listens for AgentSession conversation_item_added and mirrors speech to the backend."""

    def __init__(self, interview_id: str, mcp_client: MCPClient) -> None:
        self._interview_id = interview_id
        self._mcp = mcp_client
        self._seen_ids: set[str] = set()

    def attach(self, session: AgentSession) -> None:
        @session.on("conversation_item_added")
        def _on_item(event: ConversationItemAddedEvent) -> None:
            asyncio.create_task(self._handle_item(event))

    async def _handle_item(self, event: ConversationItemAddedEvent) -> None:
        item = event.item
        if not isinstance(item, ChatMessage):
            return

        msg_id = getattr(item, "id", None)
        if msg_id:
            if msg_id in self._seen_ids:
                return
            self._seen_ids.add(msg_id)

        role = _ROLE_MAP.get(item.role)
        if not role:
            return

        text = (item.text_content or "").strip()
        if not text:
            return

        ts = float(item.created_at or time.time())
        try:
            await self._mcp.call(
                "append_transcript_turn",
                interview_id=self._interview_id,
                role=role,
                content=text,
                ts=ts,
            )
        except Exception:
            logger.warning(
                "Failed to append transcript interview=%s role=%s",
                self._interview_id,
                role,
                exc_info=True,
            )