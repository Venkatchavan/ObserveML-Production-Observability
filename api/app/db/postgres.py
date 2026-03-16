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
        # OB-41: team members with RBAC
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS team_members (
                id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id      UUID        NOT NULL
                                REFERENCES organizations(id) ON DELETE CASCADE,
                user_email  VARCHAR(255) NOT NULL,
                role        VARCHAR(20)  NOT NULL DEFAULT 'viewer'
                                CHECK (role IN ('owner', 'analyst', 'viewer')),
                invited_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                accepted_at TIMESTAMPTZ
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_team_members_org_email
            ON team_members(org_id, user_email)
        """)
        )
        # OB-47: audit log for key rotation and GDPR events
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id     UUID        NOT NULL
                               REFERENCES organizations(id) ON DELETE CASCADE,
                action     VARCHAR(64) NOT NULL,
                actor      VARCHAR(255),
                details    TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        # OB-42: usage billing — ON DELETE RESTRICT preserves billing history
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS usage_billing (
                id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id         UUID        NOT NULL
                                   REFERENCES organizations(id) ON DELETE RESTRICT,
                billing_period VARCHAR(7)  NOT NULL,
                event_count    BIGINT      NOT NULL DEFAULT 0,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_billing_org_period
            ON usage_billing(org_id, billing_period)
        """)
        )
        # OB-48: GDPR deletion tokens — single-use with 24h cooling-off
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS deletion_tokens (
                id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id       UUID        NOT NULL
                                 REFERENCES organizations(id) ON DELETE CASCADE,
                token_hash   VARCHAR(64) NOT NULL UNIQUE,
                requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                executed_at  TIMESTAMPTZ
            )
        """)
        )
