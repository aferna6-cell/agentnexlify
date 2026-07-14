"""Tests for the Anthropic Message Batches helper (backend/services/batch_runtime.py).

The Anthropic batches client is mocked throughout -- no network, no real API
calls. Asserts: submit_batch builds the request shape and returns the batch
id; poll_batch maps MessageBatch -> BatchStatus; get_batch_results parses
per-custom_id results (succeeded/errored/other); and every failure mode is
swallowed (logged, safe fallback) rather than raised -- this module only ever
runs from offline callers and must never crash a caller's cron tick.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services import batch_runtime as br


def _fake_client(batches_mock):
    client = MagicMock()
    client.messages.batches = batches_mock
    return client


# ---------------------------------------------------------------------------
# submit_batch
# ---------------------------------------------------------------------------


def test_submit_batch_builds_request_shape_and_returns_id():
    requests = [
        {
            "custom_id": "enrich-0-sess-1",
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 120,
                "system": "classify",
                "messages": [{"role": "user", "content": "Customer: hi"}],
            },
        }
    ]

    batches_mock = MagicMock()
    batches_mock.create.return_value = SimpleNamespace(
        id="batch_123", processing_status="in_progress"
    )

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        batch_id = br.submit_batch(requests)

    assert batch_id == "batch_123"
    batches_mock.create.assert_called_once_with(requests=requests)


def test_submit_batch_empty_requests_returns_none_without_calling_client():
    with patch.object(br, "_client") as mock_client_factory:
        result = br.submit_batch([])

    assert result is None
    mock_client_factory.assert_not_called()


def test_submit_batch_too_many_requests_returns_none_without_calling_client():
    requests = [{"custom_id": str(i), "params": {}} for i in range(br.MAX_BATCH_REQUESTS + 1)]
    with patch.object(br, "_client") as mock_client_factory:
        result = br.submit_batch(requests)

    assert result is None
    mock_client_factory.assert_not_called()


def test_submit_batch_swallows_client_error():
    requests = [{"custom_id": "a", "params": {"model": "x", "max_tokens": 10, "messages": []}}]
    batches_mock = MagicMock()
    batches_mock.create.side_effect = RuntimeError("network down")

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        result = br.submit_batch(requests)

    assert result is None


# ---------------------------------------------------------------------------
# poll_batch
# ---------------------------------------------------------------------------


def test_poll_batch_maps_ended_status():
    counts = SimpleNamespace(succeeded=3, errored=1, canceled=0, expired=0, processing=0)
    batches_mock = MagicMock()
    batches_mock.retrieve.return_value = SimpleNamespace(
        id="batch_123",
        processing_status="ended",
        request_counts=counts,
        results_url="https://api.anthropic.com/results/batch_123",
    )

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        status = br.poll_batch("batch_123")

    assert status is not None
    assert status.batch_id == "batch_123"
    assert status.processing_status == "ended"
    assert status.ended is True
    assert status.succeeded == 3
    assert status.errored == 1
    assert status.results_url == "https://api.anthropic.com/results/batch_123"
    batches_mock.retrieve.assert_called_once_with("batch_123")


def test_poll_batch_maps_in_progress_status():
    counts = SimpleNamespace(succeeded=0, errored=0, canceled=0, expired=0, processing=5)
    batches_mock = MagicMock()
    batches_mock.retrieve.return_value = SimpleNamespace(
        id="batch_123",
        processing_status="in_progress",
        request_counts=counts,
        results_url=None,
    )

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        status = br.poll_batch("batch_123")

    assert status.ended is False
    assert status.processing == 5


def test_poll_batch_missing_batch_id_returns_none_without_calling_client():
    with patch.object(br, "_client") as mock_client_factory:
        result = br.poll_batch("")

    assert result is None
    mock_client_factory.assert_not_called()


def test_poll_batch_swallows_client_error():
    batches_mock = MagicMock()
    batches_mock.retrieve.side_effect = RuntimeError("timeout")

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        result = br.poll_batch("batch_123")

    assert result is None


# ---------------------------------------------------------------------------
# get_batch_results
# ---------------------------------------------------------------------------


def _succeeded_entry(custom_id, text):
    message = SimpleNamespace(content=[SimpleNamespace(text=text)])
    result = SimpleNamespace(type="succeeded", message=message)
    return SimpleNamespace(custom_id=custom_id, result=result)


def _errored_entry(custom_id, error="rate_limited"):
    result = SimpleNamespace(type="errored", error=error)
    return SimpleNamespace(custom_id=custom_id, result=result)


def _other_entry(custom_id, result_type):
    result = SimpleNamespace(type=result_type)
    return SimpleNamespace(custom_id=custom_id, result=result)


def test_get_batch_results_parses_succeeded_and_errored_per_custom_id():
    entries = [
        _succeeded_entry("enrich-0-sess-1", '{"sentiment": "positive", "intent": "booking"}'),
        _errored_entry("enrich-1-sess-2"),
    ]
    batches_mock = MagicMock()
    batches_mock.results.return_value = iter(entries)

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        results = br.get_batch_results("batch_123")

    assert set(results.keys()) == {"enrich-0-sess-1", "enrich-1-sess-2"}

    ok = results["enrich-0-sess-1"]
    assert ok.status == "succeeded"
    assert ok.text == '{"sentiment": "positive", "intent": "booking"}'
    assert ok.error is None

    bad = results["enrich-1-sess-2"]
    assert bad.status == "errored"
    assert bad.text is None
    assert bad.error == "rate_limited"


def test_get_batch_results_handles_canceled_and_expired():
    entries = [
        _other_entry("a", "canceled"),
        _other_entry("b", "expired"),
    ]
    batches_mock = MagicMock()
    batches_mock.results.return_value = iter(entries)

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        results = br.get_batch_results("batch_123")

    assert results["a"].status == "canceled"
    assert results["a"].text is None
    assert results["b"].status == "expired"


def test_get_batch_results_missing_batch_id_returns_empty_without_calling_client():
    with patch.object(br, "_client") as mock_client_factory:
        result = br.get_batch_results("")

    assert result == {}
    mock_client_factory.assert_not_called()


def test_get_batch_results_swallows_client_error_returns_empty():
    batches_mock = MagicMock()
    batches_mock.results.side_effect = RuntimeError("connection reset")

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        result = br.get_batch_results("batch_123")

    assert result == {}


def test_get_batch_results_returns_partial_on_mid_stream_failure():
    def _bad_iter():
        yield _succeeded_entry("a", "ok text")
        raise RuntimeError("stream broke")

    batches_mock = MagicMock()
    batches_mock.results.return_value = _bad_iter()

    with patch.object(br, "_client", return_value=_fake_client(batches_mock)):
        result = br.get_batch_results("batch_123")

    # first entry parsed before the stream broke is preserved, not discarded
    assert "a" in result
    assert result["a"].status == "succeeded"
