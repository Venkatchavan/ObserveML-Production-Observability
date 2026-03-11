/**
 * OB-13: Threshold configuration — create and delete alert rules.
 * Follows WCAG 2.1 AA: labelled form fields, error role=alert.
 */
import { useCallback, useEffect, useState } from "react";
import { fetchAlertRules, createAlertRule, deleteAlertRule } from "../api/client";
import type { AlertRule } from "../api/client";

const METRIC_OPTIONS = [
  { value: "avg_latency_ms", label: "Avg Latency (ms)" },
  { value: "error_rate", label: "Error Rate (0–1)" },
  { value: "cost_usd", label: "Cost per window ($)" },
];

export function ThresholdConfig() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [callSite, setCallSite] = useState("");
  const [metric, setMetric] = useState("avg_latency_ms");
  const [threshold, setThreshold] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadRules = useCallback(async () => {
    try {
      setRules(await fetchAlertRules());
    } catch {
      /* non-critical */
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseFloat(threshold);
    if (isNaN(parsed) || parsed <= 0) {
      setError("Threshold must be a positive number");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createAlertRule({
        call_site: callSite || null,
        metric,
        threshold: parsed,
        webhook_url: webhookUrl || null,
      });
      setThreshold("");
      setCallSite("");
      setWebhookUrl("");
      await loadRules();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create rule");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ruleId: string) => {
    await deleteAlertRule(ruleId);
    await loadRules();
  };

  return (
    <section aria-label="Alert threshold configuration">
      <h2 className="section-title">Alert Thresholds</h2>

      {error && (
        <div role="alert" className="error-banner">
          {error}
        </div>
      )}

      <form onSubmit={handleCreate} className="threshold-form" aria-label="Create alert rule">
        <label htmlFor="tf-callsite">Call Site (blank = any)</label>
        <input
          id="tf-callsite"
          value={callSite}
          onChange={(e) => setCallSite(e.target.value)}
          placeholder="e.g. chat-completion"
        />

        <label htmlFor="tf-metric">Metric</label>
        <select id="tf-metric" value={metric} onChange={(e) => setMetric(e.target.value)}>
          {METRIC_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <label htmlFor="tf-threshold">Threshold</label>
        <input
          id="tf-threshold"
          type="number"
          min="0"
          step="any"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
          placeholder="e.g. 500"
          required
        />

        <label htmlFor="tf-webhook">Webhook URL (optional)</label>
        <input
          id="tf-webhook"
          type="url"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://hooks.example.com/…"
        />

        <button type="submit" disabled={saving} aria-busy={saving}>
          {saving ? "Saving…" : "Add Rule"}
        </button>
      </form>

      {rules.length > 0 && (
        <div className="table-wrapper">
          <table aria-label="Existing alert rules">
            <thead>
              <tr>
                <th scope="col">Call Site</th>
                <th scope="col">Metric</th>
                <th scope="col">Threshold</th>
                <th scope="col">Webhook</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.call_site || "(any)"}</td>
                  <td>{r.metric}</td>
                  <td>{Number(r.threshold).toFixed(2)}</td>
                  <td>{r.webhook_url ? "✓" : "—"}</td>
                  <td>
                    <button
                      onClick={() => handleDelete(r.id)}
                      aria-label={`Delete rule for ${r.metric}`}
                      className="btn-danger"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
