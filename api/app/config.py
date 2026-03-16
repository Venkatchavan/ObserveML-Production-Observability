from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://observeml:observeml@localhost:5432/observeml"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "observeml"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    rate_limit_per_minute: int = 100
    # OB-32: allowed dashboard origin for SSE CORS manual check (kept for backward compat)
    dashboard_origin: str = "http://localhost:5173"
    # OB-42: Stripe billing — set STRIPE_API_KEY env var to enable live metering
    stripe_api_key: str = ""
    billing_free_tier_limit: int = 10_000  # events/month on free plan
    # OB-55: Redis cache for ClickHouse dashboard queries (60s TTL)
    redis_url: str = ""  # e.g. redis://localhost:6379/0; empty = caching disabled

    # -----------------------------------------------------------------------
    # Security hardening (Sprint 06 / SEC-01 — SEC-03)
    # -----------------------------------------------------------------------
    # SEC-01: CORS — comma-separated list of allowed origins; NEVER set to "*"
    # In production set CORS_ORIGINS to your actual frontend domain(s).
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # SEC-02: IP-level rate limit per minute (across all endpoints, pre-auth)
    # Protects against brute-force API-key guessing on every endpoint.
    ip_rate_limit_per_minute: int = 200
    # SEC-03: Trusted host validation (comma-separated FQDNs / IPs).
    # Empty string = no restriction (e.g. dev mode). Set to your domain in prod.
    # Example: "api.observeml.io,api.yourdomain.com"
    trusted_hosts: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
