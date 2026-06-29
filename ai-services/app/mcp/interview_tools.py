"""FastMCP server: temis-interview-agent-tools (14 tools)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import Settings, get_settings
from app.mcp.http_client import InterviewMCPBackend

logger = logging.getLogger(__name__)

_settings = get_settings()
_backend = InterviewMCPBackend(_settings)

interview_mcp = FastMCP(
    name="temis-interview-agent-tools",
    instructions=(
        "You are an AI interviewer on the Aurelia/Temis platform. "
        "Use these tools to observe the candidate, control the room, "
        "record transcript turns, and switch between interview and code modes."
    ),
    host=_settings.host,
    port=_settings.port,
)

_VALID_ROLES = frozenset({"agent", "candidate"})
_VALID_MODES = frozenset({"interview", "code"})


def _extract_coding(interview: dict[str, Any]) -> dict[str, Any]:
    assignment = interview.get("assignment") or {}
    coding = assignment.get("coding")
    if isinstance(coding, dict):
        return coding
    plan = interview.get("plan") or {}
    legacy = plan.get("coding_assignment")
    return legacy if isinstance(legacy, dict) else {}


@interview_mcp.tool()
async def list_active_interviews() -> list[dict[str, Any]]:
    """List interviews currently in progress.

    WHEN: Discovery at worker startup or ops dashboards.
    RETURNS: Array of {id, candidate_name, position, status, language, ...}.
    """
    return await _backend.list_active_interviews()


@interview_mcp.tool()
async def get_interview_context(interview_id: str) -> dict[str, Any]:
    """Get complete interview context: candidate, plan, assignment, status, code state.

    WHEN: Call FIRST when the agent joins the LiveKit room, before greeting.
    RETURNS: Full interview record from backend (plan.interview_brief drives Q&A).
    """
    return await _backend.get_interview(interview_id)


@interview_mcp.tool()
async def get_transcript(interview_id: str) -> dict[str, Any]:
    """Get the full conversation_history for this interview.

    WHEN: Resuming context, pre-wrap-up summary, or Inspector handoff prep.
    RETURNS: {interview_id, conversation_history: [{role, content, ts}, ...]}.
    """
    return await _backend.get_transcript(interview_id)


@interview_mcp.tool()
async def get_problem_statement(interview_id: str) -> dict[str, Any]:
    """Extract coding problem fields for spoken explanation (not raw markdown recital).

    WHEN: Immediately after switch_mode('code') — paraphrase naturally for the candidate.
    RETURNS: {title, difficulty, mode, statement, function_name, starter_code, ai_assistant_enabled}.
    """
    interview = await _backend.get_interview(interview_id)
    coding = _extract_coding(interview)
    return {
        "title": coding.get("title") or coding.get("name") or "",
        "difficulty": coding.get("difficulty") or "",
        "mode": coding.get("mode") or (interview.get("assignment") or {}).get("type") or "",
        "statement": coding.get("description") or coding.get("statement") or "",
        "function_name": coding.get("function_name") or "solution",
        "starter_code": coding.get("starter_code") or "",
        "ai_assistant_enabled": coding.get("ai_assistant_enabled"),
    }


@interview_mcp.tool()
async def get_live_snapshot(interview_id: str) -> dict[str, Any]:
    """Aggregate context + transcript + code + last run logs in one call.

    WHEN: Mid-session refresh before a follow-up question or mode transition.
    RETURNS: {context, transcript, current_code, sandbox_files, last_run_result, ui_mode}.
    """
    interview = await _backend.get_interview(interview_id)
    transcript = await _backend.get_transcript(interview_id)
    return {
        "context": interview,
        "transcript": transcript.get("conversation_history") or [],
        "current_code": interview.get("current_code"),
        "sandbox_files": interview.get("sandbox_files"),
        "last_run_result": interview.get("last_run_result"),
        "ui_mode": interview.get("ui_mode") or "interview",
        "assignment_finished": interview.get("assignment_finished", False),
    }


@interview_mcp.tool()
async def get_sandbox_files(interview_id: str) -> dict[str, Any]:
    """Get multi-file Sandpack workspace (project mode).

    WHEN: Project/cognitive assignment — before analyze_candidate_code.
    RETURNS: {sandbox_files: {path: content, ...}} or empty dict.
    """
    interview = await _backend.get_interview(interview_id)
    files = interview.get("sandbox_files")
    return {"sandbox_files": files if isinstance(files, dict) else {}}


@interview_mcp.tool()
async def get_candidate_code(interview_id: str) -> dict[str, Any]:
    """Get candidate's current Monaco editor code (DSA mode).

    WHEN: Poll every few seconds during coding phase, or before verbal follow-up.
    RETURNS: {current_code: str | null}.
    """
    interview = await _backend.get_interview(interview_id)
    return {"current_code": interview.get("current_code")}


@interview_mcp.tool()
async def get_code_run_logs(interview_id: str) -> dict[str, Any]:
    """Get last test-run result: pass/fail, stdout, stderr.

    WHEN: After the candidate runs tests in the editor.
    RETURNS: last_run_result object or null.
    """
    interview = await _backend.get_interview(interview_id)
    return {"last_run_result": interview.get("last_run_result")}


async def _analyze_code_llm(
    *,
    code: str,
    files: dict[str, Any] | None,
    focus: str | None,
    settings: Settings,
) -> dict[str, Any]:
    if not settings.llm_enabled:
        return {
            "summary": "LLM unavailable — review code manually.",
            "issues": [],
            "strengths": [],
            "suggested_questions": [],
        }

    focus_line = f"Focus area: {focus}" if focus else "General review."
    payload = files if files else {"main.py": code}
    user = f"{focus_line}\n\nCode:\n{json.dumps(payload, indent=2)[:12000]}"
    system = (
        "You review interview coding submissions. Return JSON only with keys: "
        "summary (string), issues (string[]), strengths (string[]), suggested_questions (string[]). "
        "Questions must reference actual code patterns you see."
    )
    body = {
        "model": settings.interview_llm_model,
        "temperature": 0.3,
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.interview_llm_api_key}"}
    url = f"{settings.interview_llm_base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    return {"summary": "", "issues": [], "strengths": [], "suggested_questions": []}


@interview_mcp.tool()
async def analyze_candidate_code(
    interview_id: str,
    focus: str | None = None,
) -> dict[str, Any]:
    """LLM review of candidate code for grounded follow-up questions.

    WHEN: Before asking a coding follow-up — uses sandbox_files (project) or current_code (dsa).
    RETURNS: {summary, issues, strengths, suggested_questions}.
    """
    interview = await _backend.get_interview(interview_id)
    files = interview.get("sandbox_files")
    code = interview.get("current_code") or ""
    file_map = files if isinstance(files, dict) and files else None
    if not code and not file_map:
        return {
            "summary": "No code submitted yet.",
            "issues": [],
            "strengths": [],
            "suggested_questions": ["Ask the candidate to start implementing the solution."],
        }
    return await _analyze_code_llm(
        code=code,
        files=file_map,
        focus=focus,
        settings=_settings,
    )


@interview_mcp.tool()
async def switch_mode(interview_id: str, mode: str) -> dict[str, Any]:
    """Switch candidate UI between voice interview and code editor.

    WHEN: Moving to coding phase (mode='code') or back to voice wrap-up (mode='interview').
    CONSTRAINT: If response finished=true, assignment is locked — do not switch to code to edit.
    RETURNS: {mode, finished, assignment, current_code, sandbox_files, problem}.
    """
    normalized = mode.strip().lower()
    if normalized not in _VALID_MODES:
        raise ValueError("mode must be 'interview' or 'code'")
    return await _backend.switch_mode(interview_id, mode=normalized)


@interview_mcp.tool()
async def append_transcript_turn(
    interview_id: str,
    role: str,
    content: str,
    ts: float | None = None,
) -> dict[str, Any]:
    """Append one transcript turn (agent or candidate speech).

    WHEN: After each spoken turn — survives worker crash, feeds Inspector.
    RETURNS: {ok: true}.
    """
    normalized = role.strip().lower()
    if normalized not in _VALID_ROLES:
        raise ValueError("role must be 'agent' or 'candidate'")
    if not content.strip():
        raise ValueError("content is required")
    await _backend.append_transcript_turn(
        interview_id,
        role=normalized,
        content=content.strip(),
        ts=ts,
    )
    return {"ok": True}


@interview_mcp.tool()
async def send_message_to_candidate(interview_id: str, message: str) -> dict[str, Any]:
    """Send on-screen text to candidate via LiveKit data channel and save to transcript.

    WHEN: Display a written hint, question summary, or transition notice (not spoken audio).
    RETURNS: {ok: true}.
    """
    if not message.strip():
        raise ValueError("message is required")
    await _backend.send_agent_message(interview_id, message=message.strip())
    return {"ok": True}


@interview_mcp.tool()
async def set_coding_assistant(interview_id: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable the in-editor AI coding assistant for the candidate.

    WHEN: Project challenges (enable) vs DSA (disable). Same as assignment MCP toggles.
    RETURNS: {enabled: bool}.
    """
    return await _backend.set_coding_assistant(interview_id, enabled=enabled)


@interview_mcp.tool()
async def end_interview(
    interview_id: str,
    reason: str = "completed",
    detail: str = "",
) -> dict[str, Any]:
    """End the interview session after verbal goodbye.

    WHEN: Once only, when Q&A and assignment are complete. Triggers status=completed.
    RETURNS: {ok: true}.
    """
    await _backend.end_interview(interview_id, reason=reason, detail=detail)
    return {"ok": True}


# Registry for dev HTTP shim (/mcp-http/tools/call)
INTERVIEW_TOOL_REGISTRY: dict[str, Any] = {
    "list_active_interviews": list_active_interviews,
    "get_interview_context": get_interview_context,
    "get_transcript": get_transcript,
    "get_problem_statement": get_problem_statement,
    "get_live_snapshot": get_live_snapshot,
    "get_sandbox_files": get_sandbox_files,
    "get_candidate_code": get_candidate_code,
    "get_code_run_logs": get_code_run_logs,
    "analyze_candidate_code": analyze_candidate_code,
    "switch_mode": switch_mode,
    "append_transcript_turn": append_transcript_turn,
    "send_message_to_candidate": send_message_to_candidate,
    "set_coding_assistant": set_coding_assistant,
    "end_interview": end_interview,
    # Legacy aliases (dev HTTP shim)
    "get_interview": get_interview_context,
}


async def get_interview_plan_legacy(interview_id: str) -> dict[str, Any]:
    ctx = await get_interview_context(interview_id)
    return {"plan": ctx.get("plan") or {}}


INTERVIEW_TOOL_REGISTRY["get_interview_plan"] = get_interview_plan_legacy