"""
seed_dev.py — Creates a dev org + API key and sends 50 synthetic events.

Usage:
    cd projects/Project_03_ObserveML
    docker compose up -d
    pip install httpx asyncpg
    python scripts/seed_dev.py

Prints the API key to stdout for use in the dashboard.
"""
import asyncio
import hashlib
import os
import random
import secrets
import httpx
import asyncpg

POSTGRES_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://observeml:observeml@localhost:5432/observeml",
)
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

MODELS = ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]


async def create_org_and_key() -> tuple[str, str]:
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        org_id = await conn.fetchval(
            "INSERT INTO organizations (name, plan) VALUES ($1, $2) RETURNING id::text",
            "Dev Org",
            "free",
        )
        raw_key = f"om_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        await conn.execute(
            "INSERT INTO api_keys (org_id, key_hash, name) VALUES ($1, $2, $3)",
            org_id,
            key_hash,
            "seed-key",
        )
        return org_id, raw_key
    finally:
        await conn.close()


def make_event(call_site: str, model: str) -> dict:
    latency = random.randint(100, 2000)
    tokens_in = random.randint(50, 500)
    tokens_out = random.randint(20, 200)
    return {
        "call_site": call_site,
        "model": model,
        "latency_ms": latency,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "cost_usd": round((tokens_in + tokens_out) * 0.000015, 6),
        "error": random.random() < 0.05,
        "error_code": "rate_limit" if random.random() < 0.03 else "",
        "prompt_hash": "",
    }


async def seed_events(api_key: str) -> None:
    call_sites = ["generate_summary", "classify_intent", "extract_entities"]
    events = [
        make_event(random.choice(call_sites), random.choice(MODELS))
        for _ in range(50)
    ]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/v1/ingest",
            json={"events": events},
            headers={"x-api-key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Ingest response: {data}")


async def main() -> None:
    print("Creating dev org and API key…")
    org_id, api_key = await create_org_and_key()
    print(f"Org ID : {org_id}")
    print(f"API Key: {api_key}")
    print("\nSending 50 synthetic metric events…")
    await seed_events(api_key)
    print("\nDone. Open http://localhost:5173 and paste the API key above.")


if __name__ == "__main__":
    asyncio.run(main())
