/**
 * OB-43: Usage metering dashboard panel — monthly event count + cost bar chart.
 * 333-Line Law: this file is intentionally < 80 lines.
 */

import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { fetchBillingUsage } from "../api/client";
import type { UsageStatus } from "../api/client";

export function UsageMeter() {
  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBillingUsage()
      .then(setUsage)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load usage")
      );
  }, []);

  if (error) return <p role="alert" className="error-banner">{error}</p>;
  if (!usage) return <p aria-busy="true">Loading usage…</p>;

  const pct =
    usage.free_tier_limit > 0
      ? Math.min(100, Math.round((usage.events_this_month / usage.free_tier_limit) * 100))
      : 0;

  const barData = [
    { name: "Used",  value: usage.events_this_month },
    { name: "Limit", value: usage.free_tier_limit },
  ];

  const overLimit = usage.over_limit;

  return (
    <section aria-label="Monthly usage metering">
      <h2 className="section-title">Usage Metering</h2>

      <dl className="usage-stats">
        <dt>Plan</dt>
        <dd className={overLimit ? "error-high" : ""}>{usage.plan}</dd>
        <dt>Events this month</dt>
        <dd>
          {usage.events_this_month.toLocaleString()} /{" "}
          {usage.free_tier_limit.toLocaleString()} ({pct}%)
        </dd>
        <dt>Projected cost</dt>
        <dd>${usage.projected_cost_usd.toFixed(6)}</dd>
      </dl>

      {overLimit && (
        <div role="alert" className="budget-warning">
          ⚠ Free tier limit exceeded — upgrade to Pro for unlimited events.
        </div>
      )}

      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={barData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <XAxis dataKey="name" />
          <YAxis tickFormatter={(v: number) => v.toLocaleString()} />
          <Tooltip formatter={(v: number) => v.toLocaleString()} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {barData.map((_, i) => (
              <Cell
                key={i}
                fill={i === 0 && overLimit ? "#ef4444" : "#6366f1"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
