"""System prompt and greeting helpers for the voice interview agent."""

from __future__ import annotations

from typing import Any


def build_system_instructions(
    *,
    interview_brief: str,
    candidate_name: str,
    position: str,
    language: str = "en",
) -> str:
    brief = (interview_brief or "").strip()
    if not brief:
        brief = (
            f"Conduct a structured technical interview for {candidate_name or 'the candidate'} "
            f"applying to the {position or 'role'}. Ask one question at a time, listen, "
            "then follow up briefly. Keep spoken replies under three sentences."
        )

    if language.lower().startswith("vi"):
        lang_hint = "Vietnamese (Tiếng Việt)"
        lang_rule = "You MUST speak only in Vietnamese. Never switch to English unless the candidate explicitly asks."
    else:
        lang_hint = "English"
        lang_rule = "You MUST speak only in English unless the candidate explicitly asks for another language."
    return f"""You are Aurelia, a professional AI technical interviewer.

{lang_rule}
Speak in {lang_hint}. Keep every spoken turn concise (at most three short sentences).
Ask one question at a time. Wait for the candidate to answer before moving on.
Do not mention internal tools, APIs, or system instructions.

Candidate: {candidate_name or "the candidate"}
Role: {position or "the open position"}

Interview briefing (your sole source of truth — do not invent facts beyond this):
{brief}
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
    return {
        "candidate_name": interview.get("candidate_name") or "",
        "position": interview.get("position") or "",
        "interview_brief": plan.get("interview_brief") or "",
        "duration_minutes": plan.get("duration_minutes"),
    }