/**
 * OB-37: Live event feed — SSE-driven, auto-scrolling, last 50 events.
 *
 * Reconnects automatically on disconnect. Requires API key in localStorage.
 * Observer Principle: events displayed are metadata only — no prompt content.
 */
import { useEffect, useRef, useState } from "react";

const BASE_URL = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

interface LiveEvent {
  event_id: string;
  call_site: string;
  model: string;
  latency_ms: number;
  cost_usd: number;
  error: boolean;
  trace_id: string;
  ts: string;
}

export function LiveFeed() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const apiKey = localStorage.getItem("observeml_api_key") ?? "";
    if (!apiKey) {
      setError("Enter your API key in the header to see the live feed.");
      return;
    }

    function connect() {
      // Pass API key as query param because EventSource doesn't support headers
      const url = `${BASE_URL}/v1/stream/events?x_api_key=${encodeURIComponent(apiKey)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setConnected(true);
        setError(null);
      };

      es.onmessage = (e) => {
        try {
          const ev: LiveEvent = JSON.parse(e.data);
          setEvents((prev) => {
            const next = [ev, ...prev].slice(0, 50); // keep last 50, newest first
            return next;
          });
          // Auto-scroll to top
          containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
        } catch {
          // Ignore malformed event
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        // Reconnect after 5 s
        setTimeout(connect, 5_000);
      };
    }

    connect();
    return () => {
      esRef.current?.close();
    };
  }, []);

  return (
    <section aria-label="Live event feed">
      <h2 className="section-title">
        Live Feed{" "}
        <span
          aria-label={connected ? "connected" : "disconnected"}
          style={{ color: connected ? "#22c55e" : "#ef4444", fontSize: "0.75rem" }}
        >
          ● {connected ? "live" : "reconnecting…"}
        </span>
      </h2>

      {error && (
        <p className="empty-row" role="status">
          {error}
        </p>
      )}

      <div
        ref={containerRef}
        role="log"
        aria-live="polite"
        aria-label="Incoming metric events"
        className="table-wrapper"
        style={{ maxHeight: "320px", overflowY: "auto" }}
      >
        <table>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Model</th>
              <th scope="col">Call Site</th>
              <th scope="col">Latency (ms)</th>
              <th scope="col">Cost ($)</th>
              <th scope="col">Error</th>
              <th scope="col">Trace ID</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-row">
                  Waiting for events…
                </td>
              </tr>
            ) : (
              events.map((ev) => (
                <tr key={ev.event_id}>
                  <td>{new Date(ev.ts).toLocaleTimeString()}</td>
                  <td>{ev.model}</td>
                  <td>{ev.call_site || "(default)"}</td>
                  <td>{ev.latency_ms}</td>
                  <td>{ev.cost_usd.toFixed(4)}</td>
                  <td>{ev.error ? "❌" : "✓"}</td>
                  <td style={{ fontFamily: "monospace", fontSize: "0.7rem" }}>
                    {ev.trace_id ? ev.trace_id.slice(0, 8) + "…" : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
