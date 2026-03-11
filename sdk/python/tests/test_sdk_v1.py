"""OB-24: SDK v1.0 comprehensive test suite — Python.

Covers configurable flush interval, module API, edge cases, and
re-confirms all constitutional gates from Sprint 01.
"""

import inspect
import time

import pytest

from observeml.tracker import ObserveML, prompt_hash, _FLUSH_INTERVAL_S


class TestConfigurableFlushInterval:
    """OB-17: flush_interval_s is configurable at __init__ and configure()."""

    def test_default_flush_interval(self):
        client = ObserveML(api_key="k", endpoint="http://localhost/v1/ingest")
        assert client._flush_interval_s == _FLUSH_INTERVAL_S

    def test_custom_flush_interval_stored(self):
        client = ObserveML(api_key="k", endpoint="http://localhost/v1/ingest", flush_interval_s=1.0)
        assert client._flush_interval_s == 1.0

    def test_configure_with_custom_interval(self):
        import observeml

        observeml.configure(api_key="testkey-v1", flush_interval_s=2.0)
        assert observeml._default._flush_interval_s == 2.0
        # Reset to default for other tests
        observeml.configure(api_key="testkey-v1")


class TestModuleAPI:
    """Module-level configure() / track() / prompt_hash()."""

    def test_configure_sets_singleton(self):
        import observeml

        observeml.configure(api_key="singleton-test")
        assert observeml._default is not None

    def test_track_without_configure_raises(self):
        import observeml as m

        original = m._default
        m._default = None
        try:
            with pytest.raises(RuntimeError, match="configure"):
                m.track(model="gpt-4o", latency_ms=100)
        finally:
            m._default = original

    def test_prompt_hash_returns_64_char_hex(self):
        h = prompt_hash("hello", "world")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_prompt_hash_is_deterministic(self):
        assert prompt_hash("a", "b") == prompt_hash("a", "b")

    def test_prompt_hash_differs_for_different_inputs(self):
        assert prompt_hash("a", "b") != prompt_hash("c", "d")


class TestObserverPrincipleV1:
    """Re-run constitutional content-leak gates on v1.0 SDK."""

    def test_track_signature_has_no_prompt(self):
        sig = inspect.signature(ObserveML.track)
        assert "prompt" not in sig.parameters

    def test_track_signature_has_no_response(self):
        sig = inspect.signature(ObserveML.track)
        assert "response" not in sig.parameters

    def test_payload_contains_no_forbidden_keys(self, monkeypatch):
        captured = []
        client = ObserveML(api_key="v1", endpoint="http://localhost/v1/ingest")
        orig = client._queue.put_nowait
        monkeypatch.setattr(client._queue, "put_nowait", lambda e: (captured.append(e), orig(e)))
        client.track(model="claude-3-5-sonnet", latency_ms=200)
        assert captured
        event = captured[0]
        for key in ("prompt", "response", "prompt_content", "response_content", "system_prompt"):
            assert key not in event, f"Forbidden key '{key}' in payload"


class TestEdgeCases:
    """boundary and edge-case behaviour for v1.0."""

    def test_track_minimal_kwargs(self):
        client = ObserveML(api_key="k", endpoint="http://localhost/v1/ingest")
        result = client.track(model="gpt-4o-mini", latency_ms=0)
        assert result is None

    def test_queue_full_drops_silently(self):
        client = ObserveML(api_key="k", endpoint="http://localhost/v1/ingest")
        # Overfill queue without flushing
        for _ in range(11_000):
            client.track(model="gpt-4o", latency_ms=1)
        # Should not raise or block

    def test_track_overhead_p99_under_1ms(self):
        """v1.0 constitutional gate: p99 < 1ms."""
        client = ObserveML(api_key="k", endpoint="http://localhost/v1/ingest")
        samples = [
            (lambda t0: (time.perf_counter() - t0) * 1000)(
                (
                    client.track(model="gpt-4o-mini", latency_ms=i) or time.perf_counter()  # noqa
                )
            )
            for i in range(1000)
        ]
        # Rebuild timing correctly
        samples = []
        for i in range(1000):
            t0 = time.perf_counter()
            client.track(model="gpt-4o-mini", latency_ms=i)
            samples.append((time.perf_counter() - t0) * 1000)
        samples.sort()
        p99 = samples[int(len(samples) * 0.99)]
        assert p99 < 1.0, f"p99={p99:.4f}ms exceeds 1ms constitutional limit"
