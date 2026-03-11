"""
OB-07: SDK overhead benchmark — p99 < 1ms
OB-08: SDK content-leak test — no prompt/response in transmitted payload

These are Sprint 01 constitutional gates.
Both must pass for DoD sign-off.
"""
import inspect
import time

import pytest

from observeml.tracker import ObserveML, track, prompt_hash


# ---------------------------------------------------------------------------
# OB-08  Observer Principle — no prompt/response in SDK signature or payload
# ---------------------------------------------------------------------------

class TestObserverPrinciple:
    """Content-leak test: no prompt or response in SDK parameter list or payload."""

    def test_ObserveML_track_has_no_prompt_param(self):
        sig = inspect.signature(ObserveML.track)
        assert "prompt" not in sig.parameters, (
            "Observer Principle violated: 'prompt' parameter found in ObserveML.track()"
        )

    def test_ObserveML_track_has_no_response_param(self):
        sig = inspect.signature(ObserveML.track)
        assert "response" not in sig.parameters, (
            "Observer Principle violated: 'response' parameter found in ObserveML.track()"
        )

    def test_module_track_has_no_prompt_param(self):
        sig = inspect.signature(track)
        assert "prompt" not in sig.parameters, (
            "Observer Principle violated: 'prompt' in module-level track()"
        )

    def test_module_track_has_no_response_param(self):
        sig = inspect.signature(track)
        assert "response" not in sig.parameters, (
            "Observer Principle violated: 'response' in module-level track()"
        )

    def test_enqueued_event_contains_no_prompt_key(self, monkeypatch):
        captured = []
        client = ObserveML(api_key="test-key", endpoint="http://localhost/v1/ingest")

        # Intercept the internal queue to inspect the enqueued dict
        original_put = client._queue.put_nowait

        def capturing_put(event):
            captured.append(event)
            original_put(event)

        monkeypatch.setattr(client._queue, "put_nowait", capturing_put)
        client.track(model="gpt-4o", latency_ms=200, input_tokens=100)

        assert len(captured) == 1
        event = captured[0]
        assert "prompt" not in event, "Payload contains 'prompt' key — Observer Principle violated"
        assert "response" not in event, "Payload contains 'response' key — Observer Principle violated"
        assert "prompt_content" not in event
        assert "response_content" not in event

    def test_prompt_hash_helper_exists_and_does_not_store(self):
        """prompt_hash() helper is allowed — it returns a hash, not the content."""
        h = prompt_hash("my secret prompt", "my secret response")
        assert len(h) == 64
        assert h != "my secret prompt"
        assert h != "my secret response"


# ---------------------------------------------------------------------------
# OB-07  SDK overhead — p99 < 1ms
# ---------------------------------------------------------------------------

class TestSDKOverhead:
    """track() must return in p99 < 1ms (non-blocking, queue-backed)."""

    def test_track_overhead_p99_under_1ms(self):
        client = ObserveML(api_key="test-key", endpoint="http://localhost/v1/ingest")
        samples = []

        for _ in range(1000):
            t0 = time.perf_counter()
            client.track(model="gpt-4o", latency_ms=100, input_tokens=50)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            samples.append(elapsed_ms)

        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 < 1.0, (
            f"SDK overhead p99 = {p99:.4f}ms — exceeds 1ms constitutional limit"
        )

    def test_track_returns_none(self):
        client = ObserveML(api_key="test-key", endpoint="http://localhost/v1/ingest")
        result = client.track(model="gpt-4o", latency_ms=50)
        assert result is None


# ---------------------------------------------------------------------------
# Queue behaviour tests
# ---------------------------------------------------------------------------

class TestQueueBehavior:
    def test_full_queue_does_not_block(self):
        client = ObserveML(api_key="test-key", endpoint="http://localhost/v1/ingest")
        # Drain the flush thread so queue stays full
        for _ in range(10_001):
            client.track(model="gpt-4o", latency_ms=0)
        # Should complete without blocking or raising

    def test_configure_raises_without_init(self):
        import observeml
        # Reset singleton
        observeml.tracker._default = None
        with pytest.raises(RuntimeError, match="not configured"):
            observeml.track(model="gpt-4o", latency_ms=10)
