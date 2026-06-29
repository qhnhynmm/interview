"""HTTP proxy to backend interview endpoints (MCP tools delegate here)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1/interviews"


class InterviewMCPBackend:
    """Thin async client — no local state."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        base = (
            self._settings.interview_backend_url
            or self._settings.backend_url
        ).rstrip("/")
        self._api = f"{base}{API_PREFIX}"
        self._timeout = float(getattr(self._settings, "mcp_http_timeout", 20.0))

    def _service_headers(self) -> dict[str, str]:
        key = getattr(self._settings, "internal_service_key", "").strip()
        if not key:
            return {}
        return {"X-Service-Key": key}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        url = f"{self._api}{path}"
        headers = self._service_headers() if auth else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                if response.content:
                    return response.json()
                return None
        except httpx.HTTPStatusError as exc:
            logger.warning("MCP backend %s %s → %s", method, path, exc.response.status_code)
            raise
        except Exception as exc:
            logger.warning("MCP backend %s %s error: %s", method, path, exc)
            raise

    async def list_active_interviews(self) -> list[dict[str, Any]]:
        result = await self._request("GET", "/active")
        return result if isinstance(result, list) else []

    async def get_interview(self, interview_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/{interview_id}", auth=False)
        return data if isinstance(data, dict) else {}

    async def get_transcript(self, interview_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/{interview_id}/transcript")
        return data if isinstance(data, dict) else {"conversation_history": []}

    async def append_transcript_turn(
        self,
        interview_id: str,
        *,
        role: str,
        content: str,
        ts: float | None = None,
    ) -> None:
        body: dict[str, Any] = {"role": role, "content": content}
        if ts is not None:
            body["ts"] = ts
        await self._request("POST", f"/{interview_id}/transcript/append", json=body)

    async def switch_mode(self, interview_id: str, *, mode: str) -> dict[str, Any]:
        data = await self._request(
            "POST",
            f"/{interview_id}/switch-mode",
            json={"mode": mode},
        )
        return data if isinstance(data, dict) else {"mode": mode}

    async def send_agent_message(self, interview_id: str, *, message: str) -> None:
        await self._request(
            "POST",
            f"/{interview_id}/send-agent-message",
            json={"message": message},
        )

    async def set_coding_assistant(self, interview_id: str, *, enabled: bool) -> dict[str, Any]:
        data = await self._request(
            "POST",
            f"/{interview_id}/set-assistant",
            json={"enabled": enabled},
        )
        return data if isinstance(data, dict) else {"enabled": enabled}

    async def get_coding_assistant_status(self, interview_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/{interview_id}/coding-assistant")
        return data if isinstance(data, dict) else {"enabled": False}

    async def end_interview(
        self,
        interview_id: str,
        *,
        reason: str = "completed",
        detail: str = "",
    ) -> None:
        base = (
            self._settings.interview_backend_url
            or self._settings.backend_url
        ).rstrip("/")
        url = f"{base}{API_PREFIX}/{interview_id}/end"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json={"reason": reason, "detail": detail})
            response.raise_for_status()