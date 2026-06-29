import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BackendClient:
    """Thin HTTP client — MCP tools delegate to backend API (no direct DB access)."""

    def __init__(self, settings: Settings | None = None, *, base_url: str | None = None) -> None:
        self._settings = settings or get_settings()
        if base_url:
            self._base = base_url.rstrip("/")
        else:
            self._base = (
                self._settings.interview_backend_url
                or self._settings.backend_url
            ).rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, json=json, params=params)
                response.raise_for_status()
                if response.content:
                    return response.json()
                return None
        except httpx.HTTPStatusError as exc:
            logger.warning("Backend %s %s failed: %s", method, path, exc.response.status_code)
            raise
        except Exception as exc:
            logger.warning("Backend %s %s error: %s", method, path, exc)
            raise

    async def get_interview(self, interview_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/v1/interviews/{interview_id}")

    async def end_interview(
        self,
        interview_id: str,
        *,
        reason: str = "completed",
        detail: str = "",
    ) -> None:
        await self._request(
            "POST",
            f"/api/v1/interviews/{interview_id}/end",
            json={"reason": reason, "detail": detail},
        )

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")