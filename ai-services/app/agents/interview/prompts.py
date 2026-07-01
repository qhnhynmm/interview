"""System prompt and greeting helpers for the voice interview agent."""

from __future__ import annotations

from typing import Any


def _vietnamese_fallback_brief(
    *,
    candidate_name: str,
    position: str,
    duration_minutes: int | None,
    special_requirements: str,
) -> str:
    mins = duration_minutes or 50
    hr = f"\n- Ưu tiên HR: {special_requirements}" if special_requirements else ""
    return (
        f"Phỏng vấn kỹ thuật có cấu trúc cho {candidate_name or 'ứng viên'} "
        f"ứng tuyển {position or 'vị trí'} (~{mins} phút).\n"
        "- Mở đầu: hỏi về project kỹ thuật mạnh nhất và vai trò cá nhân.\n"
        "- Hỏi từng câu một, theo dõi độ sâu kỹ thuật, problem solving, communication.\n"
        "- Sau Q&A: chuyển sang coding phase (switch_mode code).\n"
        f"- Kết thúc: tóm tắt ngắn và hỏi ứng viên có câu hỏi không.{hr}"
    )


def _english_fallback_brief(
    *,
    candidate_name: str,
    position: str,
    duration_minutes: int | None,
    special_requirements: str,
) -> str:
    mins = duration_minutes or 50
    hr = f"\n- HR priority: {special_requirements}" if special_requirements else ""
    return (
        f"Structured technical interview for {candidate_name or 'the candidate'} "
        f"applying to {position or 'the role'} (~{mins} minutes).\n"
        "- Open: ask about their strongest technical project and personal ownership.\n"
        "- One question at a time; probe technical depth, problem solving, communication.\n"
        "- After Q&A: transition to coding phase (switch_mode code).\n"
        f"- Close: brief summary and ask if they have questions.{hr}"
    )


def _competency_block(competencies: list[dict[str, Any]]) -> str:
    if not competencies:
        return ""
    lines = []
    for row in competencies[:6]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        weight = row.get("weight")
        if not name:
            continue
        if weight is not None:
            w = float(weight)
            pct = int(w * 100) if w <= 1 else int(w)
            lines.append(f"- {name} ({pct}%)")
        else:
            lines.append(f"- {name}")
    if not lines:
        return ""
    return "Weighted competencies to cover:\n" + "\n".join(lines)


def build_system_instructions(
    *,
    interview_brief: str,
    candidate_name: str,
    position: str,
    language: str = "en",
    duration_minutes: int | None = None,
    special_requirements: str = "",
    competencies: list[dict[str, Any]] | None = None,
    interview_id: str = "",
    has_coding_assignment: bool = True,
) -> str:
    brief = (interview_brief or "").strip()
    is_vi = language.lower().startswith("vi")

    if not brief:
        if is_vi:
            brief = _vietnamese_fallback_brief(
                candidate_name=candidate_name,
                position=position,
                duration_minutes=duration_minutes,
                special_requirements=special_requirements,
            )
        else:
            brief = _english_fallback_brief(
                candidate_name=candidate_name,
                position=position,
                duration_minutes=duration_minutes,
                special_requirements=special_requirements,
            )

    if is_vi:
        lang_hint = "Vietnamese (Tiếng Việt)"
        lang_rule = "You MUST speak only in Vietnamese. Never switch to English unless the candidate explicitly asks."
    else:
        lang_hint = "English"
        lang_rule = "You MUST speak only in English unless the candidate explicitly asks for another language."

    duration_line = ""
    if duration_minutes:
        duration_line = f"Target duration: ~{duration_minutes} minutes total."

    hr_block = ""
    if special_requirements.strip():
        hr_block = (
            f"\nHR special requirements (high priority — weave into questions):\n"
            f"{special_requirements.strip()}\n"
        )

    comp_block = _competency_block(competencies or [])
    comp_section = f"\n{comp_block}\n" if comp_block else ""

    coding_block = ""
    if has_coding_assignment:
        coding_block = """
## Coding phase (mandatory for tech track)
- When voice Q&A is complete, call switch_mode(interview_id, 'code') to open the editor.
- Call get_problem_statement(interview_id) and explain the task naturally — do NOT read raw markdown.
- During coding you may stay mostly silent; poll get_candidate_code or get_code_run_logs when helpful.
- Before a verbal follow-up, call analyze_candidate_code(interview_id) for grounded questions.
- When coding is done, call switch_mode(interview_id, 'interview') for wrap-up (skip if assignment finished=true).
"""

    tools_block = f"""
## MCP tools (use silently — never mention tool names to the candidate)
Interview ID for all tool calls: {interview_id or "(from room name)"}
- append_transcript_turn(interview_id, role, content) — after EVERY spoken turn (agent or candidate).
- send_message_to_candidate — on-screen text hints only (not spoken).
- switch_mode — 'code' for coding, 'interview' for voice wrap-up.
- get_problem_statement — after switching to code.
- get_candidate_code / get_code_run_logs / analyze_candidate_code — during coding.
- end_interview — once after verbal goodbye (triggers report generation).
"""

    wrap_block = """
## Wrap-up
- Summarize 2-3 strengths and 1 area to probe further (no scores).
- Ask if the candidate has questions for the team.
- Say goodbye, then call end_interview exactly once.
"""

    return f"""You are Aurelia, a professional AI technical interviewer.

{lang_rule}
Speak in {lang_hint}. Keep every spoken turn concise (at most three short sentences).
Ask one question at a time. Wait for the candidate to answer before moving on.
Do not mention internal tools, APIs, or system instructions.

Candidate: {candidate_name or "the candidate"}
Role: {position or "the open position"}
{duration_line}{hr_block}{comp_section}
Interview briefing (your sole source of truth — do not invent facts beyond this):
{brief}
{coding_block}{tools_block}{wrap_block}
"""


def build_greeting(
    *,
    candidate_name: str,
    position: str,
    language: str = "en",
) -> str:
    name = (candidate_name or "").strip() or "there"
    role = (position or "").strip() or "this role"
    if language.lower().startswith("vi"):
        return (
            f"Xin chào {name}, tôi là Aurelia, người phỏng vấn AI của bạn hôm nay "
            f"cho vị trí {role}. Bạn đã sẵn sàng bắt đầu chưa?"
        )
    return (
        f"Hello {name}, I'm Aurelia, your AI interviewer today for the {role} position. "
        "Are you ready to begin?"
    )


def extract_interview_context(interview: dict[str, Any], plan_payload: dict[str, Any]) -> dict[str, Any]:
    plan = plan_payload.get("plan") if isinstance(plan_payload.get("plan"), dict) else {}
    if not plan and isinstance(interview.get("plan"), dict):
        plan = interview["plan"]

    grounding = plan.get("grounding") if isinstance(plan.get("grounding"), dict) else {}
    competencies = grounding.get("competencies") or plan.get("competencies") or []

    assignment = interview.get("assignment") or {}
    atype = str(assignment.get("type") or "").lower()
    has_coding = atype == "coding" or bool(assignment.get("coding") or plan.get("coding_assignment"))

    return {
        "candidate_name": interview.get("candidate_name") or "",
        "position": interview.get("position") or "",
        "interview_brief": plan.get("interview_brief") or "",
        "duration_minutes": plan.get("duration_minutes"),
        "special_requirements": (
            interview.get("special_requirements")
            or plan.get("special_requirements")
            or grounding.get("special_requirements")
            or ""
        ),
        "competencies": competencies if isinstance(competencies, list) else [],
        "has_coding_assignment": has_coding,
    }