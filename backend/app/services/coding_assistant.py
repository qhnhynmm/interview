import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def fetch_code_assist(
    *,
    interview_id: str,
    messages: list[dict],
    code: str,
    language: str,
    position: str = "",
) -> str:
    settings = get_settings()
    payload = {
        "interview_id": interview_id,
        "messages": messages,
        "code": code,
        "language": language,
        "position": position,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(settings.coding_assistant_url, json=payload)
            if response.is_success:
                data = response.json()
                return data.get("message") or data.get("reply") or ""
    except Exception as exc:
        logger.warning("Coding assistant unavailable for %s: %s", interview_id, exc)

    last = messages[-1]["content"] if messages else ""
    return (
        "Try breaking the problem into smaller steps. "
        f"Consider edge cases for: {last[:80]}"
    )