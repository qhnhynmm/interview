import logging
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def trace_span(name: str, **attrs: object) -> Iterator[None]:
    """Lightweight tracing hook — swap for OpenTelemetry when otel_enabled."""
    settings = get_settings()
    if settings.otel_enabled:
        logger.info("span.start %s %s", name, attrs)
    try:
        yield
    finally:
        if settings.otel_enabled:
            logger.info("span.end %s", name)