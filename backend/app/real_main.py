"""Production ingestion API. Run with: uvicorn app.real_main:app --port 8000."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.services.production_pipeline import ProductionPipeline
from app.services.real_ingestion import fetch_telegram_updates, fetch_x_recent


pipeline = ProductionPipeline()
clients: set[WebSocket] = set()
poll_task: asyncio.Task | None = None


async def poll_authorized_sources():
    while True:
        try:
            events = []
            if os.getenv("X_BEARER_TOKEN"):
                try:
                    events.extend(await fetch_x_recent(int(os.getenv("X_FETCH_LIMIT", "50"))))
                except Exception as exc:
                    print(f"x ingestion error: {type(exc).__name__}: {exc}")
            if os.getenv("TELEGRAM_BOT_TOKEN"):
                try:
                    events.extend(await fetch_telegram_updates(int(os.getenv("TELEGRAM_FETCH_LIMIT", "50"))))
                except Exception as exc:
                    print(f"telegram ingestion error: {type(exc).__name__}: {exc}")
            for event in events:
                stored, inserted = pipeline.ingest(event)
                if inserted:
                    for client in list(clients):
                        try:
                            await client.send_json({"type": "event", "event": stored})
                        except Exception:
                            clients.discard(client)
        except Exception as exc:
            print(f"authorized ingestion error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(max(30, int(os.getenv("INGEST_POLL_SECONDS", "60"))))


@asynccontextmanager
async def lifespan(_: FastAPI):
    global poll_task
    if os.getenv("ENABLE_REAL_INGESTION", "false").lower() == "true":
        poll_task = asyncio.create_task(poll_authorized_sources())
    yield
    if poll_task:
        poll_task.cancel()


app = FastAPI(title="ImpactR Production Ingestion API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","), allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "authorized_ingestion", "x_configured": bool(os.getenv("X_BEARER_TOKEN")), "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")), "database": "sqlite_wal"}


@app.get("/events")
async def events(limit: int = Query(100, ge=1, le=1000)):
    return pipeline.recent(limit)


@app.post("/ingestion/poll")
async def poll_once():
    fetched: list[dict[str, Any]] = []
    errors = []
    if os.getenv("X_BEARER_TOKEN"):
        try:
            fetched.extend(await fetch_x_recent())
        except Exception as exc:
            errors.append({"source": "x", "error": type(exc).__name__, "detail": str(exc)})
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            fetched.extend(await fetch_telegram_updates())
        except Exception as exc:
            errors.append({"source": "telegram", "error": type(exc).__name__, "detail": str(exc)})
    inserted = [pipeline.ingest(event)[0] for event in fetched]
    return {"fetched": len(fetched), "persisted": len(inserted), "sources": sorted({event["platform"] for event in fetched}), "errors": errors}


@app.get("/sources")
async def sources():
    return [{"platform": "x", "status": "connected" if os.getenv("X_BEARER_TOKEN") else "not_configured", "authorization": "official X API v2"}, {"platform": "telegram", "status": "connected" if os.getenv("TELEGRAM_BOT_TOKEN") else "not_configured", "authorization": "official Telegram Bot API"}]


@app.get("/investigations/{investigation_id}")
async def investigation(investigation_id: str):
    posts = pipeline.recent(200)
    if not posts:
        raise HTTPException(status_code=404, detail="No persisted events available for investigation")
    platforms = sorted({post.get("platform") for post in posts})
    return {
        "id": investigation_id,
        "overview": {"title": "Live source investigation", "summary": "Evidence collected from authorized source events", "post_count": len(posts), "platform_count": len(platforms), "growth_rate": 0, "first_seen": posts[-1].get("event_time"), "last_seen": posts[0].get("event_time")},
        "why": ["Events were persisted from authorized source APIs", "Each event has a raw source payload", "Analysis metadata is stored with the event"],
        "timeline": [], "narratives": [], "signals": [], "graph": {"nodes": [], "edges": []},
        "evidence": [{**post, "timestamp": post.get("event_time"), "author_name": post.get("author_id_hash", "hashed author")} for post in posts],
    }


@app.websocket("/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept(); clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
