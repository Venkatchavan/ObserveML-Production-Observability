package io.observeml;

import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Logger;

/**
 * ObserveML Java SDK — TrackerClient (OB-46).
 *
 * <p>Observer Principle: {@code track()} accepts ONLY telemetry metadata.
 * There is intentionally no {@code prompt} or {@code response} parameter.
 *
 * <p>Thread safety: a single daemon flush thread consumes from a bounded
 * {@link BlockingQueue}. All public methods are safe to call from any thread.
 *
 * <p>333-Line Law: this file is intentionally &lt; 333 lines.
 *
 * <p>Usage:
 * <pre>{@code
 * TrackerClient tracker = new TrackerClient("obs_live_xxxx",
 *                                           "https://api.observeml.io");
 * Map<String,Object> event = new java.util.HashMap<>();
 * event.put("model",      "gpt-4o");
 * event.put("latencyMs",  320);
 * event.put("inputTokens", 150);
 * event.put("outputTokens", 80);
 * event.put("costUsd",    0.0024);
 * event.put("callSite",   "chat");
 * event.put("sessionId",  "session-abc");
 * tracker.track(event);
 * // On shutdown:
 * tracker.shutdown();
 * }</pre>
 */
public final class TrackerClient {

    private static final Logger LOG = Logger.getLogger(TrackerClient.class.getName());

    private static final int  QUEUE_CAPACITY   = 1_000;
    private static final int  BATCH_MAX        = 50;
    private static final long FLUSH_INTERVAL_MS = 500L;

    private final String                   apiKey;
    private final String                   baseUrl;
    private final BlockingQueue<Map<String, Object>> queue;
    private final AtomicBoolean            running;
    private final Thread                   worker;

    /**
     * Create a TrackerClient.
     *
     * @param apiKey  ObserveML API key (starts with {@code obs_live_}).
     * @param baseUrl Base URL, e.g. {@code https://api.observeml.io}.
     */
    public TrackerClient(String apiKey, String baseUrl) {
        this.apiKey  = apiKey;
        this.baseUrl = baseUrl.endsWith("/")
                ? baseUrl.substring(0, baseUrl.length() - 1)
                : baseUrl;
        this.queue   = new ArrayBlockingQueue<>(QUEUE_CAPACITY);
        this.running = new AtomicBoolean(true);
        this.worker  = new Thread(this::runFlushLoop, "observeml-flush");
        this.worker.setDaemon(true);
        this.worker.start();
    }

    /**
     * Enqueue one LLM inference telemetry event (non-blocking).
     *
     * <p>Accepted keys: {@code model} (String, required), {@code latencyMs} (int),
     * {@code inputTokens} (int), {@code outputTokens} (int), {@code costUsd} (double),
     * {@code callSite} (String), {@code error} (boolean), {@code errorCode} (String),
     * {@code sessionId} (String), {@code traceId} (String).
     *
     * <p>Observer Principle: there is no {@code prompt} or {@code response} key.
     *
     * @param event telemetry map — never include prompt or response text
     */
    public void track(Map<String, Object> event) {
        if (!queue.offer(event)) {
            LOG.warning("ObserveML: queue full, dropping event model="
                    + event.getOrDefault("model", "?"));
        }
    }

    /**
     * Flush remaining events and stop the worker thread.
     * Call on application shutdown for a graceful drain.
     */
    public void shutdown() {
        running.set(false);
        worker.interrupt();
        try {
            worker.join(5_000L);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    private void runFlushLoop() {
        List<Map<String, Object>> batch = new ArrayList<>(BATCH_MAX);
        while (running.get() || !queue.isEmpty()) {
            try {
                Map<String, Object> head = queue.poll(FLUSH_INTERVAL_MS, TimeUnit.MILLISECONDS);
                if (head != null) {
                    batch.add(head);
                    queue.drainTo(batch, BATCH_MAX - 1);
                    flush(batch);
                    batch.clear();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        queue.drainTo(batch);
        if (!batch.isEmpty()) {
            flush(batch);
        }
    }

    private void flush(List<Map<String, Object>> events) {
        try {
            byte[] body = toJson(events).getBytes(StandardCharsets.UTF_8);
            HttpURLConnection conn =
                    (HttpURLConnection) new URL(baseUrl + "/v1/ingest").openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("x-api-key", apiKey);
            conn.setDoOutput(true);
            conn.setConnectTimeout(5_000);
            conn.setReadTimeout(10_000);
            try (OutputStream out = conn.getOutputStream()) {
                out.write(body);
            }
            int status = conn.getResponseCode();
            if (status == 402) {
                LOG.warning("ObserveML: free tier limit exceeded — upgrade to Pro.");
            } else if (status >= 400) {
                LOG.warning("ObserveML: ingest returned HTTP " + status);
            }
        } catch (IOException e) {
            LOG.warning("ObserveML: flush failed — " + e.getMessage());
        }
    }

    // ---- JSON serialisation (no external dependencies) ----------------------

    private static String toJson(List<Map<String, Object>> events) {
        StringBuilder sb = new StringBuilder("{\"events\":[");
        for (int i = 0; i < events.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append(eventToJson(events.get(i)));
        }
        return sb.append("]}").toString();
    }

    private static String eventToJson(Map<String, Object> e) {
        StringBuilder sb = new StringBuilder("{");
        appendStr(sb,    "model",         str(e, "model",         "unknown"), true);
        appendInt(sb,    "latency_ms",    num(e, "latencyMs",     0));
        appendInt(sb,    "input_tokens",  num(e, "inputTokens",   0));
        appendInt(sb,    "output_tokens", num(e, "outputTokens",  0));
        appendDouble(sb, "cost_usd",      dbl(e, "costUsd",       0.0));
        appendStr(sb,    "call_site",     str(e, "callSite",      ""), false);
        appendBool(sb,   "error",         bool(e, "error",        false));
        appendStr(sb,    "error_code",    str(e, "errorCode",     ""), false);
        appendStr(sb,    "session_id",    str(e, "sessionId",     ""), false);
        appendStr(sb,    "trace_id",      str(e, "traceId",       ""), false);
        return sb.append('}').toString();
    }

    private static void appendStr(StringBuilder sb, String k, String v, boolean first) {
        if (!first) sb.append(',');
        sb.append('"').append(k).append("\":\"").append(escJson(v)).append('"');
    }

    private static void appendInt(StringBuilder sb, String k, int v) {
        sb.append(",\"").append(k).append("\":").append(v);
    }

    private static void appendDouble(StringBuilder sb, String k, double v) {
        sb.append(",\"").append(k).append("\":").append(v);
    }

    private static void appendBool(StringBuilder sb, String k, boolean v) {
        sb.append(",\"").append(k).append("\":").append(v);
    }

    private static String escJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    private static String str(Map<String, Object> m, String k, String def) {
        Object v = m.get(k);
        return (v instanceof String) ? (String) v : def;
    }

    private static int num(Map<String, Object> m, String k, int def) {
        Object v = m.get(k);
        return (v instanceof Number) ? ((Number) v).intValue() : def;
    }

    private static double dbl(Map<String, Object> m, String k, double def) {
        Object v = m.get(k);
        return (v instanceof Number) ? ((Number) v).doubleValue() : def;
    }

    private static boolean bool(Map<String, Object> m, String k, boolean def) {
        Object v = m.get(k);
        return (v instanceof Boolean) ? (Boolean) v : def;
    }
}
