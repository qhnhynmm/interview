"""FastMCP server: temis-assignment-agent-tools (3 tools)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.mcp.http_client import InterviewMCPBackend

_settings = get_settings()
_backend = InterviewMCPBackend(_settings)

assignment_mcp = FastMCP(
    name="temis-assignment-agent-tools",
    instructions=(
        "Toggle and inspect the candidate-facing coding assistant during assignments. "
        "Enable for project challenges; disable for unaided DSA."
    ),
    host=_settings.host,
    port=_settings.port,
)


@assignment_mcp.tool()
async def enable_coding_assistant(interview_id: str) -> dict[str, Any]:
    """Turn on the in-editor AI coding assistant.

    WHEN: Project-style assignment where guided help is allowed.
    RETURNS: {enabled: true}.
    """
    return await _backend.set_coding_assistant(interview_id, enabled=True)


@assignment_mcp.tool()
async def disable_coding_assistant(interview_id: str) -> dict[str, Any]:
    """Turn off the in-editor AI coding assistant.

    WHEN: DSA / unaided coding — candidate must solve without editor AI.
    RETURNS: {enabled: false}.
    """
    return await _backend.set_coding_assistant(interview_id, enabled=False)


@assignment_mcp.tool()
async def get_coding_assistant_status(interview_id: str) -> dict[str, Any]:
    """Read whether the coding assistant is currently enabled.

    WHEN: Before toggling or explaining rules to the candidate.
    RETURNS: {enabled: bool}.
    """
    return await _backend.get_coding_assistant_status(interview_id)


ASSIGNMENT_TOOL_REGISTRY: dict[str, Any] = {
    "enable_coding_assistant": enable_coding_assistant,
    "disable_coding_assistant": disable_coding_assistant,
    "get_coding_assistant_status": get_coding_assistant_status,
}