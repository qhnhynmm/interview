from pathlib import Path

from app.config import get_settings
from app.services.object_storage import download_bytes, download_object, is_s3_uri


def load_cv_bytes(cv_path: str | None) -> bytes:
    if not cv_path:
        return b""

    if is_s3_uri(cv_path):
        return download_bytes(cv_path)

    path = Path(cv_path)
    if path.is_absolute() and path.exists():
        return path.read_bytes()

    settings = get_settings()
    if settings.minio_enabled:
        return download_object(settings.minio_bucket_cvs, cv_path)

    if path.exists():
        return path.read_bytes()

    raise FileNotFoundError(f"CV not found: {cv_path}")