from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import ingest, metrics, alerts, compare, stream, teams, billing, org
from app.db.postgres import init_db
from app.db.clickhouse import ensure_table


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    ensure_table()
    yield


app = FastAPI(
    title="ObserveML API",
    version="1.2.0",
    description="LLM observability ingest and metrics API — metadata only, never prompt content",
    lifespan=lifespan,
)

app.include_router(ingest.router, prefix="/v1", tags=["ingest"])
app.include_router(metrics.router, prefix="/v1", tags=["metrics"])
app.include_router(alerts.router, prefix="/v1", tags=["alerts"])
app.include_router(compare.router, prefix="/v1", tags=["compare"])
app.include_router(stream.router, prefix="/v1", tags=["stream"])
app.include_router(teams.router, prefix="/v1", tags=["teams"])
app.include_router(billing.router, prefix="/v1", tags=["billing"])
app.include_router(org.router, prefix="/v1", tags=["org"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.2.0"}
