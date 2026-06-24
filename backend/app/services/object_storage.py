import logging
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_s3_client() -> BaseClient | None:
    settings = get_settings()
    if not settings.minio_enabled:
        return None
    if not settings.minio_access_key or not settings.minio_secret_key:
        logger.warning("MinIO enabled but MINIO_ACCESS_KEY / MINIO_SECRET_KEY missing")
        return None

    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        use_ssl=settings.minio_secure,
    )


def ensure_bucket(bucket: str) -> None:
    client = get_s3_client()
    if client is None:
        return
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
        logger.info("Created MinIO bucket: %s", bucket)


def upload_bytes(*, bucket: str, key: str, data: bytes, content_type: str | None = None) -> str:
    client = get_s3_client()
    if client is None:
        raise RuntimeError("MinIO client is not configured")

    ensure_bucket(bucket)
    extra: dict = {}
    if content_type:
        extra["ContentType"] = content_type
    client.put_object(Bucket=bucket, Key=key, Body=data, **extra)
    return key


def download_object(bucket: str, key: str) -> bytes:
    client = get_s3_client()
    if client is None:
        raise RuntimeError("MinIO client is not configured")
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def download_bytes(uri: str) -> bytes:
    bucket, key = parse_s3_uri(uri)
    client = get_s3_client()
    if client is None:
        raise RuntimeError("MinIO client is not configured")
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an s3 URI: {uri}")
    path = uri.removeprefix("s3://")
    bucket, _, key = path.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid s3 URI: {uri}")
    return bucket, key


def is_s3_uri(ref: str | None) -> bool:
    return bool(ref and ref.startswith("s3://"))