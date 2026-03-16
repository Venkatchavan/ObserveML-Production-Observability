# ObserveML Grafana Datasource Plugin

A Grafana datasource plugin that surfaces ObserveML metrics—avg latency, p99, error rate, cost—directly in Grafana dashboards.

---

## Installation

### From the Grafana Plugin Catalog *(coming soon)*

Search for **ObserveML** in **Configuration → Plugins**.

### Manual

```bash
# Download the dist bundle (replace VERSION):
curl -L https://github.com/observeml/grafana-plugin/releases/download/vVERSION/observeml-datasource-VERSION.zip \
  -o observeml-datasource.zip

unzip observeml-datasource.zip -d /var/lib/grafana/plugins/
systemctl restart grafana-server
```

Add to `grafana.ini` if unsigned:

```ini
[plugins]
allow_loading_unsigned_plugins = observeml-datasource
```

---

## Configuration

| Field | Description |
|-------|-------------|
| **API URL** | Base URL of your ObserveML API (e.g. `https://api.observeml.io`) |
| **API Key** | Your org-scoped API key (stored as a Grafana secure field) |

1. Go to **Configuration → Data Sources → Add data source**.
2. Search for **ObserveML**.
3. Set **API URL** and paste your **API Key**.
4. Click **Save & Test** — you should see *"Connected to ObserveML API"*.

---

## Panel Queries

### `metrics` query type

Returns one row per `(call_site, model)` with:

| Field | Type | Description |
|-------|------|-------------|
| `call_site` | string | Code location |
| `model` | string | LLM model name |
| `avg_latency_ms` | number | Mean latency |
| `p99_latency_ms` | number | P99 latency |
| `total_calls` | number | Call count |
| `error_rate` | number | 0–1 fraction |
| `total_cost_usd` | number | Accumulated cost |

Use a **Table** panel to build a live leaderboard of your models.

### `trend` query type

Returns time-series points:

| Field | Type | Description |
|-------|------|-------------|
| `time` | time | Bucket timestamp |
| `avg_latency_ms` | number | Mean latency |
| `total_calls` | number | Call count |

Use a **Time series** panel to chart latency over time. Optionally filter to a single `call_site`.

---

## Example Dashboard JSON

```json
{
  "panels": [
    {
      "title": "LLM Latency (avg)",
      "type": "timeseries",
      "targets": [
        { "refId": "A", "queryType": "trend" }
      ]
    },
    {
      "title": "Model Leaderboard",
      "type": "table",
      "targets": [
        { "refId": "B", "queryType": "metrics" }
      ]
    }
  ]
}
```

---

## Development

```bash
npm install
npm run dev        # watch mode
npm run build      # production bundle
```

Requires Node 18+ and Grafana 9+.

---

## Security

- The API Key is stored in Grafana's encrypted secure JSON store and injected as the `x-api-key` header via the backend proxy route defined in `plugin.json`.
- The plugin **never** stores prompt text, model outputs, or any PII.

---

## License

MIT © ObserveML contributors
