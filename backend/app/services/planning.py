import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

MOCK_CODING_PROBLEM = {
    "title": "Two Sum",
    "difficulty": "medium",
    "mode": "dsa",
    "ai_assistant_enabled": True,
    "description": (
        "Given an array of integers `nums` and an integer `target`, return indices of the "
        "two numbers such that they add up to `target`.\n\n"
        "You may assume each input has exactly one solution."
    ),
    "starter_code": (
        "# Write your solution here\n\n"
        "def two_sum(nums, target):\n"
        '    """Return indices of two numbers that add up to target."""\n'
        "    pass\n"
    ),
}

_MOCK_COMPETENCIES = [
    {"name": "Technical depth", "weight": 30},
    {"name": "Problem solving", "weight": 25},
    {"name": "Communication", "weight": 25},
    {"name": "Culture fit", "weight": 20},
]

_DURATION_BY_SENIORITY = {
    "junior": 45,
    "mid": 50,
    "senior": 60,
    "manager": 60,
}


def _duration_for_seniority(seniority: str | None) -> int:
    key = (seniority or "mid").strip().lower()
    return _DURATION_BY_SENIORITY.get(key, 50)


def _mock_interview_brief(
    *,
    position: str,
    seniority: str,
    special_requirements: str | None,
    language: str,
) -> str:
    hr = (special_requirements or "").strip()
    hr_line = f" HR priority: {hr}." if hr else ""
    if language.lower().startswith("vi"):
        return (
            f"**Snapshot** — Ứng viên {position}, level **{seniority}**. "
            f"Buổi phỏng vấn mock khi Planning Agent không khả dụng.{hr_line}\n\n"
            "**## Competencies (weighted)**\n"
            "- **Technical depth** — 30%\n"
            "- **Problem solving** — 25%\n"
            "- **Communication** — 25%\n"
            "- **Culture fit** — 20%\n\n"
            "**## Interview flow**\n"
            "- Warm-up: Mô tả project kỹ thuật mạnh nhất và vai trò cá nhân.\n"
            "- **[Technical depth]** MAIN: Giải thích quyết định kiến trúc quan trọng nhất.\n"
            "- **[Problem solving]** MAIN: Kể một bug khó và cách debug.\n"
            "- **[Communication]** MAIN: Giải thích trade-off cho stakeholder không kỹ thuật.\n\n"
            "**## Time budget** — ~40% Q&A, ~45% coding, ~15% wrap-up."
        )
    return (
        f"**Snapshot** — {position} candidate at **{seniority}** level. "
        f"Mock interview when Planning Agent is unavailable.{hr_line}\n\n"
        "**## Competencies (weighted)**\n"
        "- **Technical depth** — 30%\n"
        "- **Problem solving** — 25%\n"
        "- **Communication** — 25%\n"
        "- **Culture fit** — 20%\n\n"
        "**## Interview flow**\n"
        "- Warm-up: Describe your strongest technical project and personal ownership.\n"
        "- **[Technical depth]** MAIN: Explain your most important architecture decision.\n"
        "- **[Problem solving]** MAIN: Walk through a hard bug and how you debugged it.\n"
        "- **[Communication]** MAIN: Explain a trade-off to a non-technical stakeholder.\n\n"
        "**## Time budget** — ~40% Q&A, ~45% coding, ~15% wrap-up."
    )


def _mock_evaluation_brief(*, position: str, seniority: str, language: str) -> str:
    gate = "Technical depth"
    if language.lower().startswith("vi"):
        return (
            "**## Competencies & weights**\n"
            "- **Technical depth** — 30%\n"
            "- **Problem solving** — 25%\n"
            "- **Communication** — 25%\n"
            "- **Culture fit** — 20%\n\n"
            f"### Technical depth (30%)\n"
            "- **5/STRONG**: Nêu project cụ thể, số liệu, trade-off rõ.\n"
            "- **1-2/WEAK**: Mơ hồ ownership, không giải thích quyết định.\n\n"
            "**## Recommendation guide**\n"
            "- **HIRE** (≥4.0 weighted)\n"
            "- **LEAN-HIRE** (3.2–3.9)\n"
            "- **NO-HIRE** (<3.2)\n\n"
            f"**## HARD GATE** — {gate}: score ≤2 → cap LEAN-HIRE; score ≤1 → NO-HIRE\n\n"
            "**## Integrity rules** — high risk → cap overall ≤2.5; medium → cap ≤3.2\n\n"
            "**## Red flags** — claim skill không có evidence trong transcript."
        )
    return (
        "**## Competencies & weights**\n"
        "- **Technical depth** — 30%\n"
        "- **Problem solving** — 25%\n"
        "- **Communication** — 25%\n"
        "- **Culture fit** — 20%\n\n"
        f"### Technical depth (30%)\n"
        "- **5/STRONG**: Names concrete project, quantifies impact, explains trade-offs.\n"
        "- **1-2/WEAK**: Vague ownership, cannot explain decisions.\n\n"
        "**## Recommendation guide**\n"
        "- **HIRE** (≥4.0 weighted)\n"
        "- **LEAN-HIRE** (3.2–3.9)\n"
        "- **NO-HIRE** (<3.2)\n\n"
        f"**## HARD GATE** — {gate}: score ≤2 → cap at LEAN-HIRE; score ≤1 → NO-HIRE\n\n"
        "**## Integrity rules** — high risk → cap overall ≤2.5; medium → cap ≤3.2\n\n"
        "**## Red flags** — skill claims without transcript evidence."
    )


def _mock_assignment_brief(
    *,
    position: str,
    seniority: str,
    special_requirements: str | None,
) -> str:
    hr = (special_requirements or "").strip()
    focus = hr or "core stack depth under time pressure"
    return (
        "ASSIGNMENT DIRECTIVE → type: coding · mode: dsa · "
        "ai_assistant: disabled · difficulty: medium\n\n"
        f"Context: {position} at {seniority} level — probe **{focus}**. "
        "Expect a medium DSA task similar to Two Sum (reference only). "
        "Strong solution: clear structure, edge cases, verbalized trade-offs."
    )


def build_mock_plan(
    *,
    position: str,
    seniority: str | None,
    jd_text: str,
    special_requirements: str | None,
    language: str,
) -> dict:
    level = seniority or "Mid"
    duration = _duration_for_seniority(level)
    competencies = _MOCK_COMPETENCIES
    grounding = {
        "position": position,
        "seniority_level": level.lower() if level.lower() in _DURATION_BY_SENIORITY else "mid",
        "domain": "backend",
        "required_skills": [],
        "skill_gaps": [],
        "competencies": competencies,
        "assignment": {
            "type": "coding",
            "mode": "dsa",
            "ai_assistant": False,
            "difficulty": "medium",
        },
        "special_requirements": special_requirements or "",
    }
    return {
        "is_mock": True,
        "language": language,
        "position": position,
        "seniority": level,
        "duration_minutes": duration,
        "source": "mock",
        "summary": (
            f"Mock interview plan for {position}. "
            "Replace with ai-services Planning Agent when available."
        ),
        "interview_brief": _mock_interview_brief(
            position=position,
            seniority=level,
            special_requirements=special_requirements,
            language=language,
        ),
        "evaluation_brief": _mock_evaluation_brief(
            position=position,
            seniority=level,
            language=language,
        ),
        "assignment_brief": _mock_assignment_brief(
            position=position,
            seniority=level,
            special_requirements=special_requirements,
        ),
        "grounding": grounding,
        "topics": [
            {"topic": "Introduction & background", "weight": 0.15, "minutes": 3},
            {"topic": "Technical depth", "weight": 0.35, "minutes": 6},
            {"topic": "Coding exercise", "weight": 0.35, "minutes": 5},
            {"topic": "Wrap-up", "weight": 0.15, "minutes": 1},
        ],
        "competencies": [
            {"name": c["name"], "weight": c["weight"] / 100.0} for c in competencies
        ],
        "jd_excerpt": jd_text[:500],
        "special_requirements": special_requirements or "",
        "coding_assignment": MOCK_CODING_PROBLEM,
    }


async def fetch_interview_plan(
    *,
    position: str,
    seniority: str | None,
    jd_text: str,
    special_requirements: str | None,
    language: str,
    cv_text: str,
    candidate_name: str,
) -> dict:
    settings = get_settings()
    payload = {
        "position": position,
        "seniority": seniority,
        "jd_text": jd_text,
        "special_requirements": special_requirements,
        "language": language,
        "cv_markdown": cv_text,
        "cv_text": cv_text,
        "candidate_name": candidate_name,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(settings.planning_url, json=payload)
            if response.is_success:
                data = response.json()
                if isinstance(data, dict) and data.get("plan"):
                    return data["plan"]
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        logger.warning("Planning agent unavailable, using mock plan: %s", exc)

    return build_mock_plan(
        position=position,
        seniority=seniority,
        jd_text=jd_text,
        special_requirements=special_requirements,
        language=language,
    )