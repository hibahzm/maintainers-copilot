import json

from app.infra.redaction import redact
from app.infra.tracing import TraceContext, bind_trace_context, reset_trace_context, trace_event, trace_span


def test_redact_masks_api_keys_and_bearer_tokens():
    text = "api_key=sk-test bearer abc.def"

    redacted = redact(text)

    assert "sk-test" not in redacted
    assert "abc.def" not in redacted
    assert "api_key=[REDACTED]" in redacted
    assert "bearer [REDACTED]" in redacted


def test_trace_event_includes_context_and_redacts(capsys):
    tokens = bind_trace_context(TraceContext(request_id="req-1", trace_id="trace-1"))
    try:
        trace_event("demo", message="api_key=secret-value")
    finally:
        reset_trace_context(*tokens)

    record = json.loads(capsys.readouterr().out)
    assert record["event"] == "demo"
    assert record["request_id"] == "req-1"
    assert record["trace_id"] == "trace-1"
    assert record["attributes"]["message"] == "api_key=[REDACTED]"


def test_trace_span_emits_start_and_end(capsys):
    with trace_span("unit.demo", ok=True):
        pass

    events = [json.loads(line)["event"] for line in capsys.readouterr().out.splitlines()]
    assert events == ["unit.demo.start", "unit.demo.end"]
