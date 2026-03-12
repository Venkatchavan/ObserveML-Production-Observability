"""ClickHouse client — metric_events table (OB-02)."""

from typing import Any, Dict, List
import clickhouse_connect
from app.config import settings


def _client():
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def ensure_table():
    """Create metric_events table with 90-day TTL if not exists (OB-02)."""
    client = _client()
    client.command("""
        CREATE TABLE IF NOT EXISTS metric_events (
            event_id      String,
            org_id        String,
            call_site     String,
            model         String,
            latency_ms    UInt32,
            input_tokens  UInt32,
            output_tokens UInt32,
            cost_usd      Float32,
            error         Bool,
            error_code    String,
            prompt_hash   String,
            ts            DateTime64(3)
        ) ENGINE = MergeTree()
        PARTITION BY (org_id, toYYYYMMDD(ts))
        ORDER BY (org_id, call_site, ts)
        TTL toDateTime(ts) + INTERVAL 90 DAY
    """)
    # OB-36: idempotent schema migration — add trace_id if not already present
    client.command("ALTER TABLE metric_events ADD COLUMN IF NOT EXISTS trace_id String DEFAULT ''")


def insert_events(org_id: str, events: List[Dict[str, Any]]) -> None:
    rows = [
        [
            e["event_id"],
            org_id,
            e["call_site"],
            e["model"],
            e["latency_ms"],
            e["input_tokens"],
            e["output_tokens"],
            e["cost_usd"],
            e["error"],
            e["error_code"],
            e["prompt_hash"],
            e["ts"],
            e.get("trace_id", ""),  # OB-36
        ]
        for e in events
    ]
    _client().insert(
        "metric_events",
        rows,
        column_names=[
            "event_id",
            "org_id",
            "call_site",
            "model",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "error",
            "error_code",
            "prompt_hash",
            "ts",
            "trace_id",
        ],
    )


def query_metrics(org_id: str, call_site: str = None) -> List[Dict]:
    where = "WHERE org_id = %(org_id)s"
    params: Dict[str, Any] = {"org_id": org_id}
    if call_site:
        where += " AND call_site = %(call_site)s"
        params["call_site"] = call_site
    result = _client().query(
        f"""
        SELECT
            call_site,
            model,
            avg(latency_ms)              AS avg_latency_ms,
            quantile(0.5)(latency_ms)    AS p50_latency_ms,
            quantile(0.95)(latency_ms)   AS p95_latency_ms,
            quantile(0.99)(latency_ms)   AS p99_latency_ms,
            count()                      AS total_calls,
            sum(cost_usd)                AS total_cost_usd,
            countIf(error) / count()     AS error_rate
        FROM metric_events
        {where}
        GROUP BY call_site, model
        ORDER BY total_calls DESC
        LIMIT 100
    """,
        parameters=params,
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_window_stats(org_id: str, window_minutes: int = 10) -> List[Dict]:
    """OB-11: Aggregate metrics over the last window_minutes for anomaly detection."""
    result = _client().query(
        """
        SELECT
            call_site,
            avg(latency_ms)           AS avg_latency_ms,
            countIf(error) / count()  AS error_rate,
            sum(cost_usd)             AS cost_usd
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND ts >= now() - INTERVAL %(window)s MINUTE
        GROUP BY call_site
    """,
        parameters={"org_id": org_id, "window": window_minutes},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_trend(org_id: str, call_site: str = None) -> List[Dict]:
    where = "WHERE org_id = %(org_id)s AND ts >= now() - INTERVAL 7 DAY"
    params: Dict[str, Any] = {"org_id": org_id}
    if call_site:
        where += " AND call_site = %(call_site)s"
        params["call_site"] = call_site
    result = _client().query(
        f"""
        SELECT
            toStartOfHour(ts)  AS ts,
            avg(latency_ms)    AS avg_latency_ms,
            count()            AS total_calls
        FROM metric_events
        {where}
        GROUP BY ts
        ORDER BY ts ASC
    """,
        parameters=params,
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_model_comparison(org_id: str) -> List[Dict]:
    """OB-21: Aggregate metrics by model for side-by-side comparison (last 7 days)."""
    result = _client().query(
        """
        SELECT
            model,
            avg(latency_ms)           AS avg_latency_ms,
            count()                   AS total_calls,
            sum(cost_usd)             AS total_cost_usd,
            countIf(error)/count()    AS error_rate,
            avg(input_tokens)         AS avg_input_tokens,
            avg(output_tokens)        AS avg_output_tokens
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND ts >= subtractDays(now(), 7)
        GROUP BY model
        ORDER BY total_calls DESC
    """,
        parameters={"org_id": org_id},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_regression_windows(org_id: str, window_hours: int = 24) -> Dict[str, Dict]:
    """OB-22: Fetch per-call_site stats for current and baseline windows."""
    client = _client()

    def _fetch(start_h: int, end_h: int) -> List[Dict]:
        r = client.query(
            """
            SELECT
                call_site,
                avg(latency_ms)             AS lat_mean,
                stddevPop(latency_ms)       AS lat_std,
                avg(toUInt8(error))         AS err_mean,
                stddevPop(toUInt8(error))   AS err_std,
                avg(cost_usd)               AS cost_mean,
                stddevPop(cost_usd)         AS cost_std,
                count()                     AS n
            FROM metric_events
            WHERE org_id = %(org_id)s
              AND ts >= subtractHours(now(), %(end_h)s)
              AND ts < subtractHours(now(), %(start_h)s)
            GROUP BY call_site
        """,
            parameters={"org_id": org_id, "start_h": start_h, "end_h": end_h},
        )
        return [dict(zip(r.column_names, row)) for row in r.result_rows]

    windows: Dict[str, Any] = {}
    for row in _fetch(0, window_hours):
        windows.setdefault(row["call_site"], {})["current"] = row
    for row in _fetch(window_hours, window_hours * 2):
        windows.setdefault(row["call_site"], {})["baseline"] = row
    return windows


def query_cost_breakdown(org_id: str, days: int = 7) -> List[Dict]:
    """OB-23: Daily cost per model for the last N days."""
    result = _client().query(
        """
        SELECT
            model,
            toString(toDate(ts))   AS day,
            sum(cost_usd)          AS total_cost_usd,
            count()                AS total_calls,
            avg(cost_usd)          AS avg_cost_per_call
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND ts >= subtractDays(now(), %(days)s)
        GROUP BY model, day
        ORDER BY day DESC, total_cost_usd DESC
    """,
        parameters={"org_id": org_id, "days": days},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_model_routing(org_id: str) -> List[Dict]:
    """OB-35: Per-model avg latency, avg cost, error_rate for last 7 days."""
    result = _client().query(
        """
        SELECT
            model,
            avg(latency_ms)          AS avg_latency_ms,
            avg(cost_usd)            AS avg_cost_usd,
            countIf(error)/count()   AS error_rate,
            count()                  AS total_calls
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND ts >= subtractDays(now(), 7)
        GROUP BY model
        ORDER BY avg_cost_usd ASC
    """,
        parameters={"org_id": org_id},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_monthly_cost(org_id: str) -> float:
    """OB-34: Return avg daily cost for the current calendar month."""
    result = _client().query(
        """
        SELECT avg(daily_cost) AS avg_daily_cost
        FROM (
            SELECT toDate(ts) AS day, sum(cost_usd) AS daily_cost
            FROM metric_events
            WHERE org_id = %(org_id)s
              AND toMonth(ts) = toMonth(now())
              AND toYear(ts) = toYear(now())
            GROUP BY day
        )
    """,
        parameters={"org_id": org_id},
    )
    rows = result.result_rows
    if not rows or rows[0][0] is None:
        return 0.0
    return float(rows[0][0])


def query_export(org_id: str, days: int = 30) -> List[Dict]:
    """OB-38: Return last N days of raw events for CSV export."""
    # Wrap in subquery so `toString(ts) AS ts` alias does not shadow the
    # DateTime ts column used in the inner WHERE (ClickHouse alias scoping).
    result = _client().query(
        """
        SELECT
            event_id, call_site, model, latency_ms,
            input_tokens, output_tokens, cost_usd,
            error, error_code, trace_id,
            toString(ts) AS ts
        FROM (
            SELECT *
            FROM metric_events
            WHERE org_id = %(org_id)s
              AND ts >= subtractDays(now(), %(days)s)
            ORDER BY ts DESC
            LIMIT 100000
        )
    """,
        parameters={"org_id": org_id, "days": days},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]
