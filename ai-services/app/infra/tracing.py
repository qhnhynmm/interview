"""OpenTelemetry tracing for Aurelia agents — exports to Arize Phoenix via OTLP.

Custom spans use OpenInference semantic conventions so Phoenix groups agent / LLM /
tool steps correctly. When ``otel_sensitive`` is true, prompt-like attributes are
redacted (length only) before export.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Status, StatusCode

from app.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False
_tracer: trace.Tracer | None = None

_SENSITIVE_SUBSTRINGS = (
    "prompt",
    "message",
    "content",
    "system",
    "user",
    "cv",
    "jd",
    "transcript",
    "password",
    "secret",
    "token",
    "result",
    "output",
    "input",
    "arguments",
    "body",
)

_SPAN_KIND_ATTR = "openinference.span.kind"


def _try_openinference() -> Any | None:
    try:
        from openinference.semconv.trace import OpenInferenceSpanKindValues

        return OpenInferenceSpanKindValues
    except ImportError:
        return None


_OI_KINDS = _try_openinference()


def _redact_value(key: str, value: object, sensitive: bool) -> object:
    if not sensitive:
        return value
    key_l = key.lower()
    if not any(part in key_l for part in _SENSITIVE_SUBSTRINGS):
        return value
    if isinstance(value, str):
        return f"<redacted len={len(value)}>"
    if isinstance(value, (bytes, bytearray)):
        return f"<redacted bytes={len(value)}>"
    if isinstance(value, dict):
        return {k: _redact_value(str(k), v, sensitive) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, item, sensitive) for item in value[:20]]
    return "<redacted>"


def _set_attrs(span: Span, attrs: dict[str, Any], *, sensitive: bool) -> None:
    for key, value in attrs.items():
        if value is None:
            continue
        safe = _redact_value(key, value, sensitive)
        if isinstance(safe, (bool, int, float)):
            span.set_attribute(key, safe)
        else:
            span.set_attribute(key, str(safe))


def init_tracing(service_name: str = "aurelia-ai-services") -> None:
    """Configure OTLP export (Phoenix) and optional OpenLIT auto-instrumentation."""
    global _initialized, _tracer
    if _initialized:
        return

    settings = get_settings()
    if not settings.otel_enabled:
        logger.debug("Tracing disabled (otel_enabled=false)")
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception as exc:
        logger.warning("OTLP exporter unavailable (%s) — spans stay in-process only", exc)

    if settings.otel_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("aurelia.agents", "0.1.0")

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("httpx OpenTelemetry instrumentation active")
    except Exception as exc:
        logger.warning("httpx auto-instrumentation skipped: %s", exc)

    _initialized = True
    logger.info("Tracing enabled → %s (ui: http://localhost:6006)", settings.otel_otlp_endpoint)


def shutdown_tracing() -> None:
    """Flush pending spans on process exit."""
    global _initialized
    if not _initialized:
        return
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    _initialized = False


def get_tracer() -> trace.Tracer:
    if _tracer is not None:
        return _tracer
    return trace.get_tracer("aurelia.agents", "0.1.0")


def _span_kind_value(kind: str) -> str:
    if _OI_KINDS is None:
        return kind
    try:
        return getattr(_OI_KINDS, kind.upper()).value
    except AttributeError:
        return kind


@contextmanager
def trace_span(
    name: str,
    *,
    kind: str = "CHAIN",
    **attrs: object,
) -> Iterator[Span | None]:
    """Record a custom span. No-op when tracing is disabled."""
    settings = get_settings()
    if not settings.otel_enabled:
        yield None
        return

    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        span.set_attribute(_SPAN_KIND_ATTR, _span_kind_value(kind))
        _set_attrs(span, dict(attrs), sensitive=settings.otel_sensitive)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


def set_span_attributes(**attrs: object) -> None:
    """Attach attributes to the current span (e.g. after an LLM call completes)."""
    settings = get_settings()
    if not settings.otel_enabled:
        return
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    _set_attrs(span, dict(attrs), sensitive=settings.otel_sensitive)


def span_ok(message: str | None = None) -> None:
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    if message:
        span.set_attribute("aurelia.status_message", message)


def span_error(exc: BaseException) -> None:
    span = trace.get_current_span()
    if span is None or not span.is_recording():
        return
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    span.record_exception(exc)