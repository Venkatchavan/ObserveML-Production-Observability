/**
 * OB-22: Regression feed — shows statistically significant metric regressions.
 * A regression means the current 24 h window is meaningfully worse than the prior.
 */
import { useEffect, useState } from "react";
import { fetchRegressions } from "../api/client";
import type { RegressionFinding } from "../api/client";

const METRIC_LABEL: Record<string, string> = {
  latency_ms: "Avg Latency (ms)",
  error_rate: "Error Rate",
  cost_usd: "Cost (USD)",
};

export function RegressionFeed() {
  const [items, setItems] = useState<RegressionFinding[]>([]);
  const [windowHours, setWindowHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = (wh: number) => {
    setLoading(true);
    fetchRegressions(wh)
      .then((data) => { setItems(data); setError(null); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(windowHours); }, [windowHours]);

  const regressions = items.filter((i) => i.is_regression);
  const stable = items.filter((i) => !i.is_regression);

  return (
    <section aria-label="Metric regression analysis">
      <h2 className="section-title">
        Regression Detection
        <label htmlFor="reg-window" className="inline-label">
          Window:{" "}
          <select
            id="reg-window"
            value={windowHours}
            onChange={(e) => setWindowHours(Number(e.target.value))}
          >
            <option value={6}>6 h</option>
            <option value={24}>24 h</option>
            <option value={48}>48 h</option>
            <option value={168}>7 d</option>
          </select>
        </label>
      </h2>

      {loading && <p aria-busy="true">Analysing…</p>}
      {error && <div role="alert" className="error-banner">{error}</div>}

      {!loading && regressions.length === 0 && (
        <p className="empty-row status-ok">✓ No statistically significant regressions detected.</p>
      )}

      {regressions.length > 0 && (
        <div className="table-wrapper" aria-label="Detected regressions">
          <table>
            <thead>
              <tr>
                <th scope="col">Call Site</th>
                <th scope="col">Metric</th>
                <th scope="col">Current</th>
                <th scope="col">Baseline</th>
                <th scope="col">z-score</th>
                <th scope="col">p-value</th>
              </tr>
            </thead>
            <tbody>
              {regressions.map((r, i) => (
                <tr key={i} className="regression-row">
                  <td>{r.call_site || "(any)"}</td>
                  <td>{METRIC_LABEL[r.metric] ?? r.metric}</td>
                  <td className="error-high">{r.current_mean.toFixed(3)}</td>
                  <td>{r.baseline_mean.toFixed(3)}</td>
                  <td>{r.z_score.toFixed(2)}</td>
                  <td>{r.p_value.toFixed(4)}</td>
                </tr>
              ))}
              {stable.slice(0, 5).map((r, i) => (
                <tr key={`s-${i}`} className="stable-row">
                  <td>{r.call_site || "(any)"}</td>
                  <td>{METRIC_LABEL[r.metric] ?? r.metric}</td>
                  <td>{r.current_mean.toFixed(3)}</td>
                  <td>{r.baseline_mean.toFixed(3)}</td>
                  <td>{r.z_score.toFixed(2)}</td>
                  <td>{r.p_value.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
