"""OB-32: SSE router — GET /v1/stream/events (org-scoped, API key auth).

Security (Śhāstrārtha checkpoint):
  - API key required on every connection.
  - Origin header validated; Access-Control-Allow-Origin is NEVER wildcard.
  - Only the configured dashboard_origin is allowed when an Origin is present.
333-Line Law: <70 lines.
"""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.postgres import get_db
from app.services.api_key_service import validate_api_key
from app.services import event_store

router = APIRouter()

_KEEPALIVE_S = 25  # send a comment every 25 s to prevent proxy timeouts


@router.get("/stream/events")
async def stream_events(
    request: Request,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """OB-32: Server-Sent Events — last 50 events on connect, then live updates.

    Requires x-api-key header. Validates Origin (no wildcard CORS allowed).
    """
    org_id = await validate_api_key(x_api_key, db)
    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    # CORS: if Origin is present it must exactly match the configured dashboard origin
    origin = request.headers.get("origin", "")
    if origin and origin != settings.dashboard_origin:
        raise HTTPException(status_code=403, detail="Origin not permitted")

    async def event_gen() -> AsyncGenerator[str, None]:
        # Replay recent events immediately so the UI is populated on connect
        for ev in event_store.get_recent(org_id):
            yield f"data: {json.dumps(ev)}\n\n"

        q = event_store.subscribe(org_id)
        try:
            while True:
                # Exit cleanly when the client disconnects.
                # With httpx ASGITransport (tests) receive() returns http.disconnect
                # immediately; with uvicorn (prod) anyio.move_on_after(0) inside
                # is_disconnected() returns False so streaming continues normally.
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_S)
                    yield f"data: {json.dumps(ev)}\n\n"
                except asyncio.TimeoutError:
                    # Keep the connection alive through proxy idle timeouts
                    yield ": keepalive\n\n"
        finally:
            event_store.unsubscribe(org_id, q)

    resp = StreamingResponse(event_gen(), media_type="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    if origin and origin == settings.dashboard_origin:
        resp.headers["Access-Control-Allow-Origin"] = settings.dashboard_origin
    return resp
