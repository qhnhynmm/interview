"""Consume ai-services SSE endpoints and yield parsed events."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def stream_ai_post(url: str, payload: dict[str, Any], *, timeout: float) -> AsyncIterator[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            event_type: str | None = None
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                    continue
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    logger.warning("Invalid SSE JSON from %s: %s", url, line[:120])
                    continue
                if event_type and "type" not in data:
                    data["type"] = event_type
                yield data
                event_type = None