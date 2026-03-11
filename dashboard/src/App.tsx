import { useState, useEffect, useCallback } from "react";
import { MetricsChart } from "./components/MetricsChart";
import { AlertFeed } from "./components/AlertFeed";
import { ThresholdConfig } from "./components/ThresholdConfig";
import { ModelDrillDown } from "./components/ModelDrillDown";
import { ModelComparison } from "./components/ModelComparison";
import { RegressionFeed } from "./components/RegressionFeed";
import { fetchMetrics, fetchTrend } from "./api/client";
import type { MetricSummary, TrendPoint } from "./api/client";
import "./App.css";

type Tab = "overview" | "alerts" | "compare";

export default function App() {
  const [apiKey, setApiKey] = useState(
    localStorage.getItem("observeml_api_key") ?? ""
  );
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");
  const [drillCallSite, setDrillCallSite] = useState<string>("");

  const load = useCallback(async () => {
    if (!apiKey) return;
    localStorage.setItem("observeml_api_key", apiKey);
    setLoading(true);
    setError(null);
    try {
      const [m, t] = await Promise.all([fetchMetrics(), fetchTrend()]);
      setMetrics(m);
      setTrend(t.points);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000); // auto-refresh every 30 s
    return () => clearInterval(id);
  }, [load]);

  return (
    <main className="app">
      <header className="app-header">
        <h1>ObserveML</h1>
        <input
          type="password"
          placeholder="API Key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          aria-label="API Key"
          className="api-key-input"
        />
        <button onClick={load} disabled={loading} aria-busy={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </header>

      <nav aria-label="Dashboard tabs" className="tab-nav">
        <button
          role="tab"
          aria-selected={tab === "overview"}
          onClick={() => setTab("overview")}
          className={tab === "overview" ? "tab-active" : ""}
        >
          Overview
        </button>
        <button
          role="tab"
          aria-selected={tab === "alerts"}
          onClick={() => setTab("alerts")}
          className={tab === "alerts" ? "tab-active" : ""}
        >
          Alerts
        </button>
        <button
          role="tab"
          aria-selected={tab === "compare"}
          onClick={() => setTab("compare")}
          className={tab === "compare" ? "tab-active" : ""}
        >
          Compare
        </button>
      </nav>

      {error && (
        <div role="alert" className="error-banner">
          {error}
        </div>
      )}

      {tab === "overview" && (
        <>
          <section aria-label="7-day latency and call volume trend">
            <MetricsChart data={trend} title="7-Day Latency & Call Volume" />
          </section>

          <section aria-label="Call site metrics breakdown">
            <h2 className="section-title">Call Site Breakdown</h2>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Call Site</th>
                    <th scope="col">Model</th>
                    <th scope="col">Avg Latency (ms)</th>
                    <th scope="col">Total Calls</th>
                    <th scope="col">Total Cost ($)</th>
                    <th scope="col">Error Rate</th>
                    <th scope="col">Drill-down</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="empty-row">
                        {apiKey ? "No data yet — send events via SDK." : "Enter your API key above."}
                      </td>
                    </tr>
                  ) : (
                    metrics.map((m) => (
                      <tr key={`${m.call_site}-${m.model}`}>
                        <td>{m.call_site || "(default)"}</td>
                        <td>{m.model}</td>
                        <td>{m.avg_latency_ms.toFixed(1)}</td>
                        <td>{m.total_calls.toLocaleString()}</td>
                        <td>${m.total_cost_usd.toFixed(4)}</td>
                        <td className={m.error_rate > 0.05 ? "error-high" : ""}>
                          {(m.error_rate * 100).toFixed(1)}%
                        </td>
                        <td>
                          <button
                            onClick={() => setDrillCallSite(m.call_site || "")}
                            aria-label={`Drill into ${m.call_site || "default"}`}
                            className="btn-link"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {drillCallSite && <ModelDrillDown callSite={drillCallSite} />}
        </>
      )}

      {tab === "alerts" && (
        <>
          <AlertFeed />
          <ThresholdConfig />
        </>
      )}

      {tab === "compare" && (
        <>
          <ModelComparison />
          <RegressionFeed />
        </>
      )}
    </main>
  );
}
