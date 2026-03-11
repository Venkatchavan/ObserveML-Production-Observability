/**
 * OB-21: Multi-model comparison — side-by-side bar charts for
 * latency, error rate, and cost across all tracked models (last 7 days).
 */
import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { fetchModelComparison } from "../api/client";
import type { ModelComparisonRow } from "../api/client";

interface NormalisedRow {
  model: string;
  avg_latency_ms: number;
  error_pct: number;
  total_cost_usd: number;
  total_calls: number;
}

export function ModelComparison() {
  const [data, setData] = useState<NormalisedRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchModelComparison()
      .then((rows: ModelComparisonRow[]) => {
        setData(
          rows.map((r) => ({
            model: r.model,
            avg_latency_ms: Math.round(r.avg_latency_ms * 10) / 10,
            error_pct: Math.round(r.error_rate * 10_000) / 100,
            total_cost_usd: Math.round(r.total_cost_usd * 10_000) / 10_000,
            total_calls: r.total_calls,
          }))
        );
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p aria-busy="true">Loading model comparison…</p>;
  if (error) return <div role="alert" className="error-banner">{error}</div>;
  if (data.length === 0)
    return <p className="empty-row">No model data in the last 7 days.</p>;

  const chartProps = {
    data,
    margin: { top: 8, right: 24, left: 0, bottom: 8 },
  };

  return (
    <section aria-label="Multi-model metric comparison">
      <h2 className="section-title">Model Comparison — Last 7 Days</h2>

      <div className="comparison-grid">
        <figure className="compare-chart">
          <figcaption>Avg Latency (ms)</figcaption>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart {...chartProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="model" tick={{ fill: "#ccc", fontSize: 11 }} />
              <YAxis tick={{ fill: "#ccc", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }} />
              <Bar dataKey="avg_latency_ms" name="Avg Latency (ms)" fill="#7c6af7" />
            </BarChart>
          </ResponsiveContainer>
        </figure>

        <figure className="compare-chart">
          <figcaption>Error Rate (%)</figcaption>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart {...chartProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="model" tick={{ fill: "#ccc", fontSize: 11 }} />
              <YAxis tick={{ fill: "#ccc", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }} />
              <Bar dataKey="error_pct" name="Error Rate (%)" fill="#f87171" />
            </BarChart>
          </ResponsiveContainer>
        </figure>

        <figure className="compare-chart">
          <figcaption>Total Cost (USD)</figcaption>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart {...chartProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="model" tick={{ fill: "#ccc", fontSize: 11 }} />
              <YAxis tick={{ fill: "#ccc", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }} />
              <Bar dataKey="total_cost_usd" name="Total Cost ($)" fill="#4ade80" />
            </BarChart>
          </ResponsiveContainer>
        </figure>
      </div>
    </section>
  );
}
