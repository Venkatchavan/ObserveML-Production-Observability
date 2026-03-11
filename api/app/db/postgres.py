"""PostgreSQL connection + schema init (OB-03)."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create tables if not exist. Alembic used for production migrations."""
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name       VARCHAR(255) NOT NULL,
                plan       VARCHAR(20)  NOT NULL DEFAULT 'free'
                               CHECK (plan IN ('free', 'pro', 'enterprise')),
                created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id       UUID NOT NULL
                                 REFERENCES organizations(id) ON DELETE CASCADE,
                key_hash     VARCHAR(64) NOT NULL UNIQUE,
                name         VARCHAR(255),
                last_used_at TIMESTAMPTZ,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                revoked_at   TIMESTAMPTZ
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id      UUID NOT NULL
                                REFERENCES organizations(id) ON DELETE CASCADE,
                call_site   VARCHAR(255),
                metric      VARCHAR(50) NOT NULL,
                threshold   NUMERIC     NOT NULL,
                webhook_url TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash
            ON api_keys(key_hash) WHERE revoked_at IS NULL
        """)
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_alert_rules_org
            ON alert_rules(org_id)
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS alert_fired (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                rule_id       UUID REFERENCES alert_rules(id) ON DELETE SET NULL,
                org_id        UUID NOT NULL
                                  REFERENCES organizations(id) ON DELETE CASCADE,
                call_site     VARCHAR(255),
                metric        VARCHAR(50),
                current_value NUMERIC,
                threshold     NUMERIC,
                fired_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_alert_fired_org
            ON alert_fired(org_id, fired_at DESC)
        """)
        )
