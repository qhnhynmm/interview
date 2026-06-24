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


def build_mock_plan(
    *,
    position: str,
    seniority: str | None,
    jd_text: str,
    special_requirements: str | None,
    language: str,
) -> dict:
    return {
        "is_mock": True,
        "language": language,
        "position": position,
        "seniority": seniority or "Mid",
        "summary": (
            f"Mock interview plan for {position}. "
            "Replace with ai-services Planning Agent when available."
        ),
        "topics": [
            {"topic": "Introduction & background", "weight": 0.15, "minutes": 3},
            {"topic": "Technical depth", "weight": 0.35, "minutes": 6},
            {"topic": "Coding exercise", "weight": 0.35, "minutes": 5},
            {"topic": "Wrap-up", "weight": 0.15, "minutes": 1},
        ],
        "competencies": [
            {"name": "Technical depth", "weight": 0.3},
            {"name": "Problem solving", "weight": 0.25},
            {"name": "Communication", "weight": 0.25},
            {"name": "Culture fit", "weight": 0.2},
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