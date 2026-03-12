from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://observeml:observeml@localhost:5432/observeml"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "observeml"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    rate_limit_per_minute: int = 100
    # OB-32: allowed dashboard origin for SSE CORS (never wildcard)
    dashboard_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
