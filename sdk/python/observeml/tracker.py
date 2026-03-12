"""ObserveML tracker — fire-and-forget metric SDK.

Observer Principle:
  track() has NO prompt or response parameters.
  The SDK captures: model, latency, tokens, cost, error flags.
  Nothing else. Ever.
"""

import hashlib
import queue
import random
import threading
import time
from typing import Optional

import httpx

_DEFAULT_ENDPOINT = "https://api.observeml.io/v1/ingest"
_BATCH_SIZE = 100
_FLUSH_INTERVAL_S = 5.0


class ObserveML:
    def __init__(
        self,
        api_key: str,
        endpoint: str = _DEFAULT_ENDPOINT,
        flush_interval_s: float = _FLUSH_INTERVAL_S,  # OB-17: configurable
        sample_rate: float = 1.0,  # OB-31: head-based sampling (0.0–1.0)
    ) -> None:
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("sample_rate must be between 0.0 and 1.0")
        self._api_key = api_key
        self._endpoint = endpoint
        self._flush_interval_s = flush_interval_s
        self._sample_rate = sample_rate
        self._queue: queue.Queue = queue.Queue(maxsize=10_000)
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def track(
        self,
        *,
        model: str,
        latency_ms: int,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        error: bool = False,
        error_code: str = "",
        call_site: str = "",
        prompt_hash: str = "",
        trace_id: str = "",  # OB-36: OpenTelemetry trace propagation
        # reason: prompt/response parameters are intentionally absent.
        # Observer Principle: this SDK captures metadata ONLY.
    ) -> None:
        """Enqueue a metric event. Non-blocking. Returns immediately."""
        # OB-31: head-based sampling — drop deterministically, never block caller
        if self._sample_rate < 1.0 and random.random() >= self._sample_rate:
            return
        event = {
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "error": error,
            "error_code": error_code,
            "call_site": call_site,
            "prompt_hash": prompt_hash,
            "trace_id": trace_id,
        }
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass  # Drop silently — never block the caller

    def _flush_loop(self) -> None:
        while True:
            time.sleep(self._flush_interval_s)
            self._flush()

    def _flush(self) -> None:
        batch = []
        try:
            while len(batch) < _BATCH_SIZE:
                batch.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        if not batch:
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    self._endpoint,
                    json={"events": batch},
                    headers={"x-api-key": self._api_key},
                )
        except Exception:
            pass  # Fire-and-forget: network errors silently dropped in v1


# ---------- Module-level convenience API ----------

_default: Optional[ObserveML] = None


def configure(
    api_key: str,
    endpoint: str = _DEFAULT_ENDPOINT,
    flush_interval_s: float = _FLUSH_INTERVAL_S,
    sample_rate: float = 1.0,  # OB-31
) -> None:
    """Initialize the module-level singleton client."""
    global _default
    _default = ObserveML(
        api_key=api_key,
        endpoint=endpoint,
        flush_interval_s=flush_interval_s,
        sample_rate=sample_rate,
    )


def track(
    *,
    model: str,
    latency_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    error: bool = False,
    error_code: str = "",
    call_site: str = "",
    prompt_hash: str = "",
    trace_id: str = "",  # OB-36
) -> None:
    """Module-level track() — requires configure() to be called first."""
    if _default is None:
        raise RuntimeError("ObserveML not configured. Call observeml.configure(api_key=...) first.")
    _default.track(
        model=model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        error=error,
        error_code=error_code,
        call_site=call_site,
        prompt_hash=prompt_hash,
        trace_id=trace_id,
    )


def prompt_hash(prompt: str, response: str = "") -> str:
    """Hash prompt+response for dedup WITHOUT transmitting content.

    Example:
        h = observeml.prompt_hash(my_prompt, llm_response)
        observeml.track(model="gpt-4o", latency_ms=200, prompt_hash=h)
    """
    return hashlib.sha256(f"{prompt}{response}".encode()).hexdigest()
