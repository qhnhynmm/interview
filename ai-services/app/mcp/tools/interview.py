from typing import Any, Awaitable, Callable

from app.infra.backend_client import BackendClient

ToolFn = Callable[..., Awaitable[Any]]

_client = BackendClient()


async def get_interview(interview_id: str) -> dict[str, Any]:
    return await _client.get_interview(interview_id)


async def get_interview_plan(interview_id: str) -> dict[str, Any]:
    data = await _client.get_interview(interview_id)
    return {"plan": data.get("plan", {})}


async def get_assignment_state(interview_id: str) -> dict[str, Any]:
    data = await _client.get_interview(interview_id)
    return {
        "assignment": data.get("assignment"),
        "assignment_finished": data.get("assignment_finished"),
        "current_code": data.get("current_code"),
    }


# Scaffold: remaining tools delegate to backend as they are implemented.
_STUB_NAMES = [
    "update_interview_status",
    "save_transcript_turn",
    "push_data_message",
    "record_proctoring_event",
    "start_assignment",
    "submit_assignment",
    "save_code_snapshot",
    "save_sandbox_files",
    "save_cognitive_answers",
    "finalize_recording",
    "end_interview",
    "get_time_remaining",
]


async def _not_implemented(**kwargs: Any) -> dict[str, Any]:
    return {"ok": False, "error": "MCP tool not wired to backend yet", "kwargs": kwargs}


INTERVIEW_TOOLS: dict[str, ToolFn] = {
    "get_interview": get_interview,
    "get_interview_plan": get_interview_plan,
    "get_assignment_state": get_assignment_state,
    **{name: _not_implemented for name in _STUB_NAMES},
}