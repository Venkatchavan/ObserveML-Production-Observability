"""Shared helpers and pytest fixtures for ObserveML integration tests.

Both test_integration.py and test_sprint04.py import helpers from here and
receive fixtures via pytest's automatic conftest discovery.
"""

import hashlib
import os
import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.clickhouse import ensure_table
from app.db.postgres import init_db
from app.main import app

# ---------------------------------------------------------------------------
# Helpers (imported directly by test modules)
# ---------------------------------------------------------------------------

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://observeml:observeml@localhost:5432/observeml",
)


def _make_client() -> httpx.AsyncClient:
    """Return an AsyncClient wired to the ASGI app in-process — no TCP."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        timeout=10.0,
    )


async def _get_session() -> AsyncSession:
    engine = create_async_engine(DB_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


async def _create_org_and_key(db: AsyncSession) -> tuple[str, str]:
    org_id = str(uuid.uuid4())
    raw_key = f"test-{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    await db.execute(
        text("INSERT INTO organizations (id, name) VALUES (:id, :name)"),
        {"id": org_id, "name": "integration-test-org"},
    )
    await db.execute(
        text("INSERT INTO api_keys (org_id, key_hash) VALUES (:org_id, :key_hash)"),
        {"org_id": org_id, "key_hash": key_hash},
    )
    await db.commit()
    return org_id, raw_key


async def _create_alert_rule(db: AsyncSession, org_id: str, metric: str, threshold: float) -> str:
    result = await db.execute(
        text(
            "INSERT INTO alert_rules (org_id, metric, threshold) "
            "VALUES (:org_id, :metric, :threshold) RETURNING id"
        ),
        {"org_id": org_id, "metric": metric, "threshold": threshold},
    )
    await db.commit()
    return str(result.fetchone()[0])


# ---------------------------------------------------------------------------
# Fixtures (auto-discovered by pytest for all test modules in this directory)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def db_init():
    """Create all DB tables once for the whole test module."""
    await init_db()
    ensure_table()


@pytest.fixture(scope="module")
async def test_credentials(db_init):
    """Seed a fresh org + API key; shared across the module."""
    db = await _get_session()
    try:
        org_id, raw_key = await _create_org_and_key(db)
        yield org_id, raw_key
    finally:
        await db.close()
