import json
import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI-compatible chat client (Gemini or MaaS gateway)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.llm_api_key}"}

    def _chat_url(self) -> str:
        return f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"

    async def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        body = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self._chat_url(),
                    headers=self._auth_headers(),
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as exc:
            logger.warning("LLM chat_json failed (%s): %s", model, exc)
            return None

    async def chat_text(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float = 60.0,
    ) -> str | None:
        if not self.enabled:
            return None

        body = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self._chat_url(),
                    headers=self._auth_headers(),
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
                return payload["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("LLM chat_text failed (%s): %s", model, exc)
            return None