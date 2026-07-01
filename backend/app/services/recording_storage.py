"""Persist interview camera recordings (chunked upload + MinIO finalize)."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.services.object_storage import upload_bytes

logger = logging.getLogger(__name__)


def _chunk_dir(interview_id: str) -> Path:
    settings = get_settings()
    base = settings.storage_path / "recordings" / interview_id / "chunks"
    base.mkdir(parents=True, exist_ok=True)
    return base


def append_recording_chunk(interview_id: str, data: bytes) -> None:
    if not data:
        return
    chunk_dir = _chunk_dir(interview_id)
    existing = sorted(chunk_dir.glob("part_*.webm"))
    idx = len(existing)
    (chunk_dir / f"part_{idx:05d}.webm").write_bytes(data)


def finalize_recording(interview_id: str, final_blob: bytes | None = None) -> str | None:
    """Merge chunks (if any) or use provided blob; upload to MinIO. Returns s3 URI."""
    settings = get_settings()
    chunk_dir = _chunk_dir(interview_id)
    parts = sorted(chunk_dir.glob("part_*.webm"))

    if final_blob:
        payload = final_blob
    elif parts:
        payload = b"".join(p.read_bytes() for p in parts)
    else:
        return None

    if not payload:
        return None

    key = f"{interview_id}/recording.webm"
    try:
        if settings.minio_enabled:
            upload_bytes(
                bucket=settings.minio_bucket_recordings,
                key=key,
                data=payload,
                content_type="video/webm",
            )
            uri = f"s3://{settings.minio_bucket_recordings}/{key}"
        else:
            local = settings.storage_path / "recordings" / interview_id / "recording.webm"
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(payload)
            uri = str(local)

        for part in parts:
            part.unlink(missing_ok=True)
        logger.info("recording_saved interview=%s bytes=%d", interview_id, len(payload))
        return uri
    except Exception as exc:
        logger.warning("recording_finalize_failed interview=%s err=%s", interview_id, exc)
        return None