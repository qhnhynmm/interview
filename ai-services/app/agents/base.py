import logging
from typing import Any

from app.infra.llm.client import LLMClient
from app.infra.tracing import trace_span

logger = logging.getLogger(__name__)


class AgentBase:
    """Shared helpers for MAF-style agents (structured I/O + optional LLM)."""

    name: str = "base"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    async def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def _maybe_llm_json(
        self,
        *,
        span: str,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any] | None:
        with trace_span(span, model=model):
            return await self.llm.chat_json(
                model=model,
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )