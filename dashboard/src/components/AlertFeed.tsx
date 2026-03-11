/**
 * OB-13: Alert feed — shows the 50 most recent threshold breaches.
 * Polls every 30 s. Accessible: role=log, aria-live=polite.
 */
import { useEffect, useState } from "react";
import { fetchAlertFeed, deleteAlertRule } from "../api/client";
import type { AlertFeedItem } from "../api/client";

interface Props {
  onRefreshRules?: () => void;
}

export function AlertFeed({ onRefreshRules }: Props) {
  const [items, setItems] = useState<AlertFeedItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await fetchAlertFeed();
      setItems(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load alerts");
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  const metricLabel = (m: string) =>
    ({ avg_latency_ms: "Avg Latency (ms)", error_rate: "Error Rate", cost_usd: "Cost ($)" }[m] ?? m);

  if (error) {
    return (
      <div role="alert" className="error-banner">
        {error}
      </div>
    );
  }

  return (
    <section aria-label="Recent anomaly alerts">
      <h2 className="section-title">Alert Feed</h2>
      {items.length === 0 ? (
        <p className="empty-row">No alerts fired yet — configure thresholds below.</p>
      ) : (
        <div
          role="log"
          aria-live="polite"
          aria-label="Alert events"
          className="table-wrapper"
        >
          <table>
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Call Site</th>
                <th scope="col">Metric</th>
                <th scope="col">Value</th>
                <th scope="col">Threshold</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="alert-row">
                  <td>{new Date(item.fired_at).toLocaleString()}</td>
                  <td>{item.call_site || "(any)"}</td>
                  <td>{metricLabel(item.metric)}</td>
                  <td className="error-high">{Number(item.current_value).toFixed(2)}</td>
                  <td>{Number(item.threshold).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
