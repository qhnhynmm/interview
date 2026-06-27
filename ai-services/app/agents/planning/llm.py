import asyncio
import logging
import time
from typing import Any

from agent_framework.openai import OpenAIChatCompletionClient

from app.config import Settings, get_settings
from app.infra.tracing import set_span_attributes, span_error, trace_span

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
                model=self._settings.planning_model_effective,
                api_key=self._settings.llm_api_key,
                base_url=self._settings.llm_base_url,
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
            effective_model = model or settings.planning_model_effective
        effective_temp = temperature if temperature is not None else settings.planning_temperature
        if max_tokens is None and name == "planning_analyst":
            effective_max = settings.planning_analyst_max_tokens
        else:
            effective_max = max_tokens or settings.planning_max_tokens
        effective_timeout = timeout or settings.planning_request_timeout

        with trace_span(
            f"planning.llm.{name}",
            kind="LLM",
            agent=name,
            model=effective_model,
            max_tokens=effective_max,
            timeout_s=effective_timeout,
            user_message=user_message,
            instructions=instructions,
        ):
            async with _LLM_SEMAPHORE:
                started = time.perf_counter()
                try:
                    client = self._get_client()
                    if model and model != settings.planning_model_effective:
                        client = OpenAIChatCompletionClient(
                            model=effective_model,
                            api_key=settings.llm_api_key,
                            base_url=settings.llm_base_url,
                        )
                    agent = client.as_agent(name=name, instructions=instructions)
                    coro = agent.run(user_message)
                    result: Any = await asyncio.wait_for(coro, timeout=effective_timeout)
                    text = getattr(result, "text", None) or str(result)
                    elapsed = time.perf_counter() - started
                    output = text.strip() if text else None
                    set_span_attributes(
                        latency_ms=round(elapsed * 1000, 1),
                        output_chars=len(output) if output else 0,
                        success=bool(output),
                    )
                    logger.info("planning.llm %s ok in %.2fs", name, elapsed)
                    return output
                except TimeoutError:
                    logger.warning("planning.llm %s timeout after %.0fs", name, effective_timeout)
                    set_span_attributes(success=False, error="timeout")
                    return None
                except Exception as exc:
                    logger.warning("planning.llm %s failed: %s", name, exc)
                    span_error(exc)
                    set_span_attributes(success=False, error=str(exc))
                    return None