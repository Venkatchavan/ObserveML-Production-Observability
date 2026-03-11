/**
 * OB-18: Per-model timeline drill-down chart.
 * Shows hourly avg_latency and call volume for a selected model.
 */
import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { fetchTrend } from "../api/client";
import type { TrendPoint } from "../api/client";

interface Props {
  callSite: string;
}

export function ModelDrillDown({ callSite }: Props) {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!callSite) return;
    setLoading(true);
    fetchTrend(callSite)
      .then((r) => {
        setData(r.points);
        setError(null);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load trend");
      })
      .finally(() => setLoading(false));
  }, [callSite]);

  if (!callSite) return null;

  const formatTs = (ts: string) =>
    new Date(ts).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" });

  return (
    <section aria-label={`Drill-down timeline for ${callSite}`}>
      <h2 className="section-title">
        Call Site: <code>{callSite}</code> — 7-Day Hourly Timeline
      </h2>

      {error && (
        <div role="alert" className="error-banner">
          {error}
        </div>
      )}

      {loading && <p aria-busy="true">Loading timeline…</p>}

      {!loading && data.length > 0 && (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="ts"
              tickFormatter={formatTs}
              tick={{ fill: "#ccc", fontSize: 11 }}
              minTickGap={60}
            />
            <YAxis
              yAxisId="latency"
              orientation="left"
              tick={{ fill: "#ccc", fontSize: 11 }}
              label={{ value: "ms", angle: -90, position: "insideLeft", fill: "#ccc" }}
            />
            <YAxis
              yAxisId="calls"
              orientation="right"
              tick={{ fill: "#ccc", fontSize: 11 }}
              label={{ value: "calls", angle: 90, position: "insideRight", fill: "#ccc" }}
            />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }}
              labelFormatter={formatTs}
            />
            <Legend wrapperStyle={{ color: "#ccc" }} />
            <Line
              yAxisId="latency"
              type="monotone"
              dataKey="avg_latency_ms"
              name="Avg Latency (ms)"
              stroke="#7c6af7"
              dot={false}
              strokeWidth={2}
            />
            <Line
              yAxisId="calls"
              type="monotone"
              dataKey="total_calls"
              name="Total Calls"
              stroke="#4ade80"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {!loading && data.length === 0 && !error && (
        <p className="empty-row">No data in the last 7 days for this call site.</p>
      )}
    </section>
  );
}
