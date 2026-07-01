import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


MOCK_ASSIGNMENT = {
    "type": "coding",
    "summary": "Mock DSA assignment — ai-services unavailable.",
    "coding": {
        "mode": "dsa",
        "title": "Two Sum",
        "difficulty": "easy",
        "statement": (
            "Given an array of integers `nums` and an integer `target`, return indices of the "
            "two numbers such that they add up to `target`."
        ),
        "function_name": "two_sum",
        "starter_code": "def two_sum(nums: list[int], target: int) -> list[int]:\n    pass\n",
        "starter_files": {},
        "test_cases": [
            {"label": "Basic", "inputs": [[2, 7, 11, 15], 9], "expected": [0, 1]},
        ],
        "ai_assistant_enabled": False,
        "allowed_resources": ["Python standard library"],
    },
    "cognitive": None,
    "source": "mock",
}


async def fetch_assignment(
    *,
    interview_id: str,
    position: str,
    seniority: str | None,
    jd_text: str,
    cv_text: str,
    assignment_brief: str = "",
    special_requirements: str | None = None,
    language: str = "en",
) -> dict:
    settings = get_settings()
    payload = {
        "interview_id": interview_id,
        "position": position,
        "level": seniority,
        "jd_text": jd_text,
        "cv_markdown": cv_text,
        "cv_text": cv_text,
        "assignment_brief": assignment_brief,
        "special_requirements": special_requirements,
        "language": language,
    }
    url = f"{settings.ai_service_url.rstrip('/')}{settings.assignment_endpoint}"
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(url, json=payload)
            if response.is_success:
                data = response.json()
                if isinstance(data, dict) and data.get("assignment"):
                    return data["assignment"]
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        logger.warning("Assignment agent unavailable, using mock assignment: %s", exc)

    return MOCK_ASSIGNMENT