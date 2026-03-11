import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TrendPoint } from "../api/client";

interface Props {
  data: TrendPoint[];
  title?: string;
}

export function MetricsChart({ data, title }: Props) {
  const formatted = data.map((p) => ({
    ...p,
    time: new Date(p.ts).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));

  return (
    <div className="chart-wrapper" role="region" aria-label={title ?? "Metrics chart"}>
      {title && <h2 className="chart-title">{title}</h2>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formatted} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#94a3b8" }} />
          <YAxis
            yAxisId="latency"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            label={{ value: "ms", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
          />
          <YAxis
            yAxisId="calls"
            orientation="right"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            label={{ value: "calls", angle: 90, position: "insideRight", fill: "#94a3b8" }}
          />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Legend />
          <Line
            yAxisId="latency"
            type="monotone"
            dataKey="avg_latency_ms"
            stroke="#6366f1"
            name="Avg Latency (ms)"
            dot={false}
            strokeWidth={2}
          />
          <Line
            yAxisId="calls"
            type="monotone"
            dataKey="total_calls"
            stroke="#22c55e"
            name="Total Calls"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
