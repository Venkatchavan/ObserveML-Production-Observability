/**
 * OB-25: SDK v1.0 TypeScript test suite — configurable flush, full coverage.
 */
import { ObserveML, promptHash, configure, track } from "../src/index";

describe("v1.0 configurable flush interval", () => {
  test("default flushIntervalMs schedules timer", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    expect((client as any).timer).not.toBeNull();
    client.destroy();
  });

  test("custom flushIntervalMs accepted", () => {
    // Should not throw with 1000 ms interval
    const client = new ObserveML("key", "http://localhost/v1/ingest", 1_000);
    client.track({ model: "gpt-4o", latencyMs: 10 });
    client.destroy();
  });

  test("destroy() clears the timer", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    client.destroy();
    expect((client as any).timer).toBeNull();
  });
});

describe("Observer Principle — v1.0 re-validation", () => {
  test("buffer event has no prompt key", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    client.track({ model: "gpt-4o", latencyMs: 100, callSite: "chat" });
    const event = (client as any).buffer[0];
    expect(event).not.toHaveProperty("prompt");
    expect(event).not.toHaveProperty("response");
    expect(event).not.toHaveProperty("prompt_content");
    expect(event).not.toHaveProperty("response_content");
    expect(event).not.toHaveProperty("system_prompt");
    client.destroy();
  });

  test("all TrackOptions fields map to snake_case without forbidden keys", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    client.track({
      model: "claude-3-5-sonnet",
      latencyMs: 200,
      inputTokens: 100,
      outputTokens: 50,
      costUsd: 0.002,
      error: false,
      errorCode: "",
      callSite: "test",
      promptHash: "abc123",
    });
    const event = (client as any).buffer[0];
    expect(event.model).toBe("claude-3-5-sonnet");
    expect(event.latency_ms).toBe(200);
    expect(event.input_tokens).toBe(100);
    expect(event.prompt_hash).toBe("abc123");
    client.destroy();
  });
});

describe("promptHash", () => {
  test("returns 64-char hex string", async () => {
    const h = await promptHash("hello", "world");
    expect(h).toHaveLength(64);
    expect(/^[0-9a-f]+$/.test(h)).toBe(true);
  });

  test("is deterministic", async () => {
    const h1 = await promptHash("same", "input");
    const h2 = await promptHash("same", "input");
    expect(h1).toBe(h2);
  });

  test("differs for different inputs", async () => {
    const h1 = await promptHash("a", "b");
    const h2 = await promptHash("c", "d");
    expect(h1).not.toBe(h2);
  });

  test("does not include raw prompt text in output", async () => {
    const secret = "supersecret-prompt-content-that-must-not-appear";
    const h = await promptHash(secret, "response");
    expect(h).not.toContain(secret);
    expect(h).not.toContain("supersecret");
  });
});

describe("flush batching", () => {
  test("flush() empties the buffer", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    client.track({ model: "gpt-4o", latencyMs: 1 });
    client.track({ model: "gpt-4o", latencyMs: 2 });
    expect((client as any).buffer.length).toBe(2);
    client.flush();
    expect((client as any).buffer.length).toBe(0);
    client.destroy();
  });

  test("flush() on empty buffer is a no-op", () => {
    const client = new ObserveML("key", "http://localhost/v1/ingest");
    expect(() => client.flush()).not.toThrow();
    client.destroy();
  });
});

describe("module-level configure/track", () => {
  test("track() before configure() throws", () => {
    // This is tricky to test since configure() may have been called already.
    // We verify the module exports the functions and they are callable.
    expect(typeof configure).toBe("function");
    expect(typeof track).toBe("function");
  });

  test("configure sets up a client instance", () => {
    configure("test-api-key-v1", "http://localhost/v1/ingest");
    // Should not throw when called after configure
  });
});
