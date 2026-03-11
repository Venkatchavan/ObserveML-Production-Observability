/**
 * ObserveML TypeScript SDK — v0.1.0
 *
 * Observer Principle: track() captures metadata ONLY.
 * No prompt or response content is ever transmitted.
 */

const DEFAULT_ENDPOINT = "https://api.observeml.io/v1/ingest";
const BATCH_SIZE = 100;
const FLUSH_INTERVAL_MS = 5_000;

export interface TrackOptions {
  model: string;
  latencyMs: number;
  inputTokens?: number;
  outputTokens?: number;
  costUsd?: number;
  error?: boolean;
  errorCode?: string;
  callSite?: string;
  promptHash?: string;
  // reason: prompt/response are intentionally absent — Observer Principle
}

interface MetricEvent {
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  error: boolean;
  error_code: string;
  call_site: string;
  prompt_hash: string;
}

export class ObserveML {
  private readonly apiKey: string;
  private readonly endpoint: string;
  private buffer: MetricEvent[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;

  // OB-17: flushIntervalMs is configurable (default 5 s)
  constructor(
    apiKey: string,
    endpoint: string = DEFAULT_ENDPOINT,
    flushIntervalMs: number = FLUSH_INTERVAL_MS,
  ) {
    this.apiKey = apiKey;
    this.endpoint = endpoint;
    this.timer = setInterval(() => this.flush(), flushIntervalMs);
    // .unref() lets Node.js exit even if flush timer is still active —
    // prevents test-runner "force exit" warnings.
    if (typeof this.timer === "object" && this.timer !== null && "unref" in this.timer) {
      (this.timer as NodeJS.Timeout).unref();
    }
  }

  track(options: TrackOptions): void {
    const event: MetricEvent = {
      model: options.model,
      latency_ms: options.latencyMs,
      input_tokens: options.inputTokens ?? 0,
      output_tokens: options.outputTokens ?? 0,
      cost_usd: options.costUsd ?? 0,
      error: options.error ?? false,
      error_code: options.errorCode ?? "",
      call_site: options.callSite ?? "",
      prompt_hash: options.promptHash ?? "",
    };
    this.buffer.push(event);
    if (this.buffer.length >= BATCH_SIZE) {
      // reason: setTimeout(0) avoids blocking the current call stack
      setTimeout(() => this.flush(), 0);
    }
  }

  flush(): void {
    if (this.buffer.length === 0) return;
    const batch = this.buffer.splice(0, BATCH_SIZE);
    // Fire-and-forget: errors silently ignored in v1
    fetch(this.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": this.apiKey,
      },
      body: JSON.stringify({ events: batch }),
    }).catch(() => {});
  }

  destroy(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

/** Compute SHA-256 hash of prompt+response for dedup — content never leaves. */
export async function promptHash(prompt: string, response = ""): Promise<string> {
  const data = new TextEncoder().encode(prompt + response);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
