"""OB-11: Sliding-window anomaly detection — evaluated after each ingest batch."""
from app.db.clickhouse import query_window_stats
from app.db.postgres import AsyncSessionLocal
from app.services.alert_dispatcher import dispatch_alert
from sqlalchemy import text

WINDOW_MINUTES = 10
SUPPORTED_METRICS = {"avg_latency_ms", "error_rate", "cost_usd"}


async def run_anomaly_check(org_id: str) -> None:
    """Check alert_rules thresholds against the last WINDOW_MINUTES of activity.

    Uses its own DB session so it can safely run in a FastAPI BackgroundTask
    after the response is returned.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT id, call_site, metric, threshold, webhook_url "
                "FROM alert_rules WHERE org_id = :org_id"
            ),
            {"org_id": org_id},
        )
        rules = result.fetchall()
        if not rules:
            return

        stats = query_window_stats(org_id, window_minutes=WINDOW_MINUTES)
        if not stats:
            return

        for rule in rules:
            metric = rule.metric
            if metric not in SUPPORTED_METRICS:
                continue
            threshold = float(rule.threshold)

            for stat in stats:
                # None call_site on a rule means "any call_site triggers"
                if rule.call_site and stat["call_site"] != rule.call_site:
                    continue
                current_value = float(stat.get(metric, 0.0))
                if current_value > threshold:
                    await dispatch_alert(
                        rule_id=str(rule.id),
                        org_id=org_id,
                        call_site=stat["call_site"],
                        metric=metric,
                        current_value=current_value,
                        threshold=threshold,
                        webhook_url=rule.webhook_url,
                        db=db,
                    )
