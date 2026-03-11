/**
 * OB-08: Observer Principle — no prompt/response in transmitted payload
 * OB-07: SDK overhead — track() non-blocking
 */
import { ObserveML, promptHash, configure, track } from "../src/index";

describe("Observer Principle — OB-08", () => {
  test("TrackOptions has no prompt or response properties in payload", () => {
    const client = new ObserveML("test-key", "http://localhost/v1/ingest");
    client.track({ model: "gpt-4o", latencyMs: 200 });
    const event = (client as any).buffer[0];

    expect(event).not.toHaveProperty("prompt");
    expect(event).not.toHaveProperty("response");
    expect(event).not.toHaveProperty("prompt_content");
    expect(event).not.toHaveProperty("response_content");
    client.destroy();
  });

  test("track() accepts only declared TrackOptions keys", () => {
    const client = new ObserveML("test-key", "http://localhost/v1/ingest");
    // TypeScript compile-time enforcement is the primary guard.
    // This runtime check confirms the shape at the buffer level.
    client.track({
      model: "claude-3-5-sonnet",
      latencyMs: 150,
      inputTokens: 100,
      outputTokens: 60,
      costUsd: 0.002,
    });
    const event = (client as any).buffer[0];
    const keys = Object.keys(event);
    const forbidden = ["prompt", "response", "prompt_content", "response_content"];
    for (const k of forbidden) {
      expect(keys).not.toContain(k);
    }
    client.destroy();
  });
});

describe("SDK Overhead — OB-07", () => {
  test("track() returns synchronously with no blocking", () => {
    const client = new ObserveML("test-key", "http://localhost/v1/ingest");
    const samples: number[] = [];
    for (let i = 0; i < 500; i++) {
      const t0 = performance.now();
      client.track({ model: "gpt-4o", latencyMs: i });
      samples.push(performance.now() - t0);
    }
    samples.sort((a, b) => a - b);
    const p99 = samples[Math.floor(samples.length * 0.99)];
    // < 5ms in unit test env (no real network)
    expect(p99).toBeLessThan(5);
    client.destroy();
  });
});

describe("configure / track module API", () => {
  test("track() throws if not configured", () => {
    // Reset module singleton via dynamic require
    jest.resetModules();
    const m = require("../src/index");
    expect(() => m.track({ model: "gpt-4o", latencyMs: 10 })).toThrow(
      "not configured"
    );
  });
});

describe("promptHash helper", () => {
  test("returns 64-char hex string", async () => {
    const h = await promptHash("hello world", "response");
    expect(h).toHaveLength(64);
    expect(h).toMatch(/^[a-f0-9]+$/);
  });

  test("is deterministic", async () => {
    const h1 = await promptHash("same prompt", "same response");
    const h2 = await promptHash("same prompt", "same response");
    expect(h1).toBe(h2);
  });
});
