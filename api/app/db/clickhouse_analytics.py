"""Advanced analytics queries — split from clickhouse.py to honour the 333-Line Law.

Contains: OB-44/45/48 (moved from Sprint 05) + OB-51/52 new Sprint 06 queries.
333-Line Law: this file is intentionally < 200 lines.
"""

from typing import Dict, List

from app.db.clickhouse import _client


# ---------------------------------------------------------------------------
# Sprint 05 functions (moved here to keep clickhouse.py < 333 lines)
# ---------------------------------------------------------------------------


def query_session_summary(org_id: str, session_id: str) -> Dict:
    """OB-45: Cost, call count, avg latency for a session."""
    result = _client().query(
        """
        SELECT
            session_id,
            count()                AS call_count,
            avg(latency_ms)        AS avg_latency_ms,
            sum(cost_usd)          AS total_cost_usd,
            countIf(error)/count() AS error_rate
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND session_id = %(session_id)s
        GROUP BY session_id
    """,
        parameters={"org_id": org_id, "session_id": session_id},
    )
    rows = result.result_rows
    if not rows:
        return {}
    return dict(zip(result.column_names, rows[0]))


def query_prompt_hashes(org_id: str, limit: int = 10) -> List[Dict]:
    """OB-44: Top-N most-repeated prompt hashes (dedup frequency). No prompt text."""
    result = _client().query(
        """
        SELECT
            prompt_hash,
            count() AS frequency
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND prompt_hash != ''
        GROUP BY prompt_hash
        ORDER BY frequency DESC
        LIMIT %(limit)s
    """,
        parameters={"org_id": org_id, "limit": limit},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def count_events_this_month(org_id: str) -> int:
    """OB-42: Count ingested events for the current billing period (calendar month)."""
    result = _client().query(
        """
        SELECT count() AS n
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND toMonth(ts) = toMonth(now())
          AND toYear(ts) = toYear(now())
    """,
        parameters={"org_id": org_id},
    )
    rows = result.result_rows
    if not rows:
        return 0
    return int(rows[0][0])


def delete_org_events(org_id: str) -> None:
    """OB-48: GDPR — delete all metric events for the org from ClickHouse."""
    _client().command(
        "ALTER TABLE metric_events DELETE WHERE org_id = %(org_id)s",
        parameters={"org_id": org_id},
    )


# ---------------------------------------------------------------------------
# Sprint 06 — intelligence layer queries
# ---------------------------------------------------------------------------


def query_daily_cost_14d(org_id: str) -> List[Dict]:
    """OB-52: Daily cost totals for the last 14 days (feed for linear regression)."""
    result = _client().query(
        """
        SELECT
            toString(toDate(ts)) AS day,
            sum(cost_usd)        AS daily_cost
        FROM metric_events
        WHERE org_id = %(org_id)s
          AND ts >= subtractDays(now(), 14)
        GROUP BY day
        ORDER BY day ASC
    """,
        parameters={"org_id": org_id},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def query_anomaly_context(
    org_id: str, call_site: str = None, window_minutes: int = 60
) -> List[Dict]:
    """OB-51: Per call_site+model stats for the last window_minutes (root-cause feed)."""
    where = "WHERE org_id = %(org_id)s AND ts >= now() - INTERVAL %(window)s MINUTE"
    params: Dict = {"org_id": org_id, "window": window_minutes}
    if call_site:
        where += " AND call_site = %(call_site)s"
        params["call_site"] = call_site
    result = _client().query(
        f"""
        SELECT
            call_site,
            model,
            avg(latency_ms)              AS avg_latency_ms,
            quantile(0.99)(latency_ms)   AS p99_latency_ms,
            countIf(error) / count()     AS error_rate,
            count()                      AS call_count,
            avg(cost_usd)                AS avg_cost_usd
        FROM metric_events
        {where}
        GROUP BY call_site, model
        ORDER BY p99_latency_ms DESC
        LIMIT 20
    """,
        parameters=params,
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]
