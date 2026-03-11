"""API key validation — org_id always derived server-side from key hash."""

import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional


def hash_api_key(key: str) -> str:
    # reason: SHA-256 only. Plaintext never stored.
    return hashlib.sha256(key.encode()).hexdigest()


async def validate_api_key(key: str, db: AsyncSession) -> Optional[str]:
    """Return org_id (str) if key is valid and not revoked, else None."""
    key_hash = hash_api_key(key)
    result = await db.execute(
        text("""
            SELECT ak.org_id::text
            FROM   api_keys ak
            WHERE  ak.key_hash = :hash
              AND  ak.revoked_at IS NULL
        """),
        {"hash": key_hash},
    )
    row = result.fetchone()
    if not row:
        return None
    await db.execute(
        text("UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = :hash"),
        {"hash": key_hash},
    )
    await db.commit()
    return row[0]
