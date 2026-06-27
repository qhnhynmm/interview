from app.infra.tracing import init_tracing, trace_span


def test_trace_span_noop_when_disabled():
    init_tracing()
    with trace_span("test.span", kind="CHAIN", secret="should-not-export") as span:
        assert span is None