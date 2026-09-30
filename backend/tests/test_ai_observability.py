"""Tests for AI observability logging (spec §34)."""

from app.services.ai_observability import AIObservability


async def test_log_and_summarize(db_session):
    obs = AIObservability(db_session)
    await obs.log_event(request_type="generation", model="mock-llm", latency_ms=120, token_count=400)
    await obs.log_event(request_type="classification", model="mock-llm", success=False, error_kind="timeout")
    await obs.log_event(request_type="embed", model="mock-llm", latency_ms=50, token_count=100)

    summary = await obs.summary()
    assert summary["total_calls"] == 3
    assert summary["successful_calls"] == 2
    assert summary["failed_calls"] == 1
    assert summary["total_tokens"] == 500
    assert summary["avg_latency_ms"] is not None


async def test_log_returns_record(db_session):
    obs = AIObservability(db_session)
    record = await obs.log_event(request_type="tool", success=True)
    assert record.id is not None
    assert record.success is True
    assert record.request_type == "tool"
