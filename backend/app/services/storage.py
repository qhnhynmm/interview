from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.services.object_storage import upload_bytes

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def save_cv(interview_id: str, upload: UploadFile) -> tuple[str, str, bytes]:
    """Save CV and return (filename, cv_path, raw_bytes).

    cv_path is a MinIO object key (e.g. itv-abc/resume.pdf) when MinIO is enabled,
    otherwise an absolute local filesystem path.
    """
    settings = get_settings()
    safe_name = Path(upload.filename or "cv.bin").name
    content = upload.file.read()
    suffix = Path(safe_name).suffix.lower()
    content_type = upload.content_type or CONTENT_TYPES.get(suffix)

    if settings.minio_enabled:
        key = f"{interview_id}/{safe_name}"
        try:
            upload_bytes(
                bucket=settings.minio_bucket_cvs,
                key=key,
                data=content,
                content_type=content_type,
            )
            return safe_name, key, content
        except Exception:
            pass  # fall through to local disk

    dest_dir = settings.storage_path / "cvs" / interview_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe_name
    dest.write_bytes(content)
    return safe_name, str(dest), content