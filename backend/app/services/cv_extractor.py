import base64
import json
import logging
from pathlib import Path

import httpx

from app.config import get_settings
from app.schemas.cv import CVFields

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

EXTRACTION_PROMPT = """Extract structured information from this CV/resume.

Return JSON with exactly these fields:
- name: candidate full name (string or null)
- email: email address (string or null)
- phone: phone number (string or null)
- summary: professional summary (string or null)
- skills: list of skill strings
- experience: list of experience entries (role, company, dates, highlights)
- education: list of education entries
- raw_text: full plain-text content of the CV, preserving reading order

Use null for missing scalar fields and empty lists when none found.
Keep raw_text complete — do not truncate."""


def _mime_type(filename: str, content_type: str | None) -> str:
    if content_type:
        return content_type
    suffix = Path(filename).suffix.lower()
    return CONTENT_TYPES.get(suffix, "application/octet-stream")


def _normalize_str_list(items: object) -> list[str]:
    if not items:
        return []
    if not isinstance(items, list):
        return [str(items)]

    result: list[str] = []
    for item in items:
        if isinstance(item, str):
            result.append(item.strip())
        elif isinstance(item, dict):
            parts = [str(v).strip() for v in item.values() if v]
            result.append(" — ".join(parts) if parts else json.dumps(item, ensure_ascii=False))
        else:
            result.append(str(item))
    return [entry for entry in result if entry]


def _parse_cv_fields(data: dict) -> CVFields:
    return CVFields(
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        summary=data.get("summary"),
        skills=_normalize_str_list(data.get("skills")),
        experience=_normalize_str_list(data.get("experience")),
        education=_normalize_str_list(data.get("education")),
        raw_text=str(data.get("raw_text") or ""),
    )


def _fallback_extract(content: bytes, filename: str, mime: str) -> CVFields:
    if mime == "text/plain" or filename.lower().endswith(".txt"):
        text = content.decode("utf-8", errors="replace")[:50000]
        return CVFields(raw_text=text)
    return CVFields(raw_text=f"[CV file: {Path(filename).name}]")


async def _extract_with_gemini(content: bytes, filename: str, mime: str) -> CVFields:
    settings = get_settings()
    if not settings.gemini_api_key:
        return _fallback_extract(content, filename, mime)

    encoded = base64.b64encode(content).decode("ascii")
    body = {
        "contents": [
            {
                "parts": [
                    {"inline_data": {"mime_type": mime, "data": encoded}},
                    {"text": EXTRACTION_PROMPT},
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    url = GEMINI_URL.format(model=settings.gemini_model)
    try:
        async with httpx.AsyncClient(timeout=settings.gemini_request_timeout) as client:
            response = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            fields = _parse_cv_fields(data)
            if not fields.raw_text.strip():
                fields.raw_text = _fallback_extract(content, filename, mime).raw_text
            return fields
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response is not None else str(exc)
        logger.warning("Gemini HTTP %s, using fallback: %s", exc.response.status_code, detail)
        return _fallback_extract(content, filename, mime)
    except Exception as exc:
        logger.warning("Gemini CV extraction failed, using fallback: %s", exc)
        return _fallback_extract(content, filename, mime)


async def extract_cv(content: bytes, filename: str, content_type: str | None = None) -> CVFields:
    mime = _mime_type(filename, content_type)
    return await _extract_with_gemini(content, filename, mime)