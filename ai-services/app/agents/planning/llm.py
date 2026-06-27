import asyncio
import logging
import time
from typing import Any

from agent_framework.openai import OpenAIChatCompletionClient

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_LLM_SEMAPHORE = asyncio.Semaphore(2)


class PlanningLLM:
    """MAF OpenAIChatCompletionClient wrapper with cross-request concurrency cap."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: OpenAIChatCompletionClient | None = None

    @property
    def enabled(self) -> bool:
        return self._settings.llm_enabled

    def _get_client(self) -> OpenAIChatCompletionClient:
        if self._client is None:
            self._client = OpenAIChatCompletionClient(
                model=self._settings.planning_model,
                api_key=self._settings.openai_api_key,
                base_url=self._settings.openai_base_url,
            )
        return self._client

    async def run_agent(
        self,
        *,
        name: str,
        instructions: str,
        user_message: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str | None:
        if not self.enabled:
            return None

        settings = self._settings
        if model is None and name == "planning_analyst":
            effective_model = settings.planning_analyst_effective_model
        else:
            effective_model = model or settings.planning_model
        effective_temp = temperature if temperature is not None else settings.planning_temperature
        if max_tokens is None and name == "planning_analyst":
            effective_max = settings.planning_analyst_max_tokens
        else:
            effective_max = max_tokens or settings.planning_max_tokens
        effective_timeout = timeout or settings.planning_request_timeout

        async with _LLM_SEMAPHORE:
            started = time.perf_counter()
            try:
                client = self._get_client()
                if model and model != settings.planning_model:
                    client = OpenAIChatCompletionClient(
                        model=effective_model,
                        api_key=settings.openai_api_key,
                        base_url=settings.openai_base_url,
                    )
                agent = client.as_agent(name=name, instructions=instructions)
                coro = agent.run(user_message)
                result: Any = await asyncio.wait_for(coro, timeout=effective_timeout)
                text = getattr(result, "text", None) or str(result)
                elapsed = time.perf_counter() - started
                logger.info("planning.llm %s ok in %.2fs", name, elapsed)
                return text.strip() if text else None
            except TimeoutError:
                logger.warning("planning.llm %s timeout after %.0fs", name, effective_timeout)
                return None
            except Exception as exc:
                logger.warning("planning.llm %s failed: %s", name, exc)
                return None