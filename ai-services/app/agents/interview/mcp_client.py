"""HTTP client for MCP toolbox (dev: POST /mcp-http/tools/call; prod: LiveKit MCPServerHTTP SSE)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        base = self._settings.mcp_sse_url.rstrip("/")
        # Dev HTTP shim lives alongside SSE mount (replace /mcp/sse → /mcp-http/tools/call).
        self._call_url = base.replace("/mcp/sse", "/mcp-http/tools/call")

    async def call(self, name: str, **arguments: Any) -> Any:
        payload = {"name": name, "arguments": arguments}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self._call_url, json=payload)
                response.raise_for_status()
                body = response.json()
                return body.get("result")
        except Exception as exc:
            logger.warning("MCP tool %s failed: %s", name, exc)
            raise

    async def get_interview_context(self, interview_id: str) -> dict[str, Any]:
        result = await self.call("get_interview_context", interview_id=interview_id)
        return result if isinstance(result, dict) else {}

    async def get_interview(self, interview_id: str) -> dict[str, Any]:
        return await self.get_interview_context(interview_id)

    async def get_interview_plan(self, interview_id: str) -> dict[str, Any]:
        result = await self.call("get_interview_plan", interview_id=interview_id)
        return result if isinstance(result, dict) else {}