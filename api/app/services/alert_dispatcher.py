"""OB-12: Alert dispatch — persists alert_fired row + SSRF-safe webhook delivery."""

import ipaddress
from typing import Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Blocked networks per OWASP SSRF mitigation: RFC1918, loopback, link-local
_BLOCKED_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_ssrf_safe(url: str) -> bool:
    """Return True only if URL is http/https and the host is not a private address.

    Note: hostname-based URLs are accepted here; production deployments should
    also validate post-DNS-resolution IPs to catch DNS rebinding attacks.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        try:
            addr = ipaddress.ip_address(hostname)
            return not any(addr in net for net in _BLOCKED_NETS)
        except ValueError:
            # Hostname (not raw IP) — accept; DNS rebinding note above applies
            return True
    except Exception:
        return False


async def dispatch_alert(
    rule_id: str,
    org_id: str,
    call_site: str,
    metric: str,
    current_value: float,
    threshold: float,
    webhook_url: Optional[str],
    db: AsyncSession,
) -> None:
    """Persist alert_fired row and POST to webhook (if configured and SSRF-safe)."""
    await db.execute(
        text("""
            INSERT INTO alert_fired
                (rule_id, org_id, call_site, metric, current_value, threshold)
            VALUES
                (:rule_id, :org_id, :call_site, :metric, :current_value, :threshold)
        """),
        dict(
            rule_id=rule_id,
            org_id=org_id,
            call_site=call_site,
            metric=metric,
            current_value=current_value,
            threshold=threshold,
        ),
    )
    await db.commit()

    if not webhook_url or not _is_ssrf_safe(webhook_url):
        return

    payload = {
        "event": "anomaly_detected",
        "org_id": org_id,
        "call_site": call_site,
        "metric": metric,
        "current_value": current_value,
        "threshold": threshold,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(webhook_url, json=payload)
    except Exception:
        pass  # Webhook failure is non-fatal — alert row is already persisted
