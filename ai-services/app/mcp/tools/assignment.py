from typing import Any, Awaitable, Callable

from app.agents.assignment.agent import AssignmentAgent
from app.schemas.api.assignment import AssignmentGenerateRequest

ToolFn = Callable[..., Awaitable[Any]]
_agent = AssignmentAgent()


async def generate_assignment(
    interview_id: str,
    mode: str = "dsa",
    plan: dict | None = None,
    language: str = "en",
) -> dict[str, Any]:
    assignment, meta = await _agent.run(
        AssignmentGenerateRequest(
            interview_id=interview_id,
            mode=mode,
            plan=plan or {},
            language=language,
        )
    )
    return {"assignment": assignment.model_dump(), "meta": meta}


async def _not_implemented(**kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": "MCP assignment tool not implemented", "kwargs": kwargs}


ASSIGNMENT_TOOLS: dict[str, ToolFn] = {
    "generate_assignment": generate_assignment,
    "validate_submission": _not_implemented,
    "run_hidden_tests": _not_implemented,
}