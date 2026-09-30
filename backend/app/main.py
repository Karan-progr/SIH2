from __future__ import annotations

import asyncio
import os
import time
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.engine import SentinelEngine


engine = SentinelEngine()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await engine.startup()
    yield
    await engine.shutdown()


app = FastAPI(title="ImpactR Intelligence API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_error(_, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal service error", "type": type(exc).__name__})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "impactr-api", "mode": engine.mode, "synthetic": False}


@app.get("/sources")
async def sources():
    return engine.source_status()


@app.get("/events")
async def events(limit: int = Query(30, ge=1, le=200)):
    return engine.events(limit)


@app.get("/events/live")
async def live_events(limit: int = Query(30, ge=1, le=200)):
    return engine.events(limit)


@app.get("/topics")
async def topics():
    return engine.topics()


@app.get("/topics/rising")
async def rising_topics():
    return engine.rising_topics()


@app.get("/sentiment/timeline")
async def sentiment_timeline():
    return engine.sentiment_timeline()


@app.get("/narratives")
async def narratives():
    return engine.narratives()


@app.get("/narratives/{narrative_id}")
async def narrative(narrative_id: str):
    item = engine.narrative(narrative_id)
    if not item:
        raise HTTPException(404, "Narrative not found")
    return item


@app.get("/graph/{topic_id}")
async def graph(topic_id: str):
    return engine.graph(topic_id)


@app.get("/investigations/{investigation_id}")
async def investigation(investigation_id: str):
    item = engine.investigation(investigation_id)
    if not item:
        raise HTTPException(404, "Investigation not found")
    return item


@app.get("/signals")
async def signals():
    return engine.signals()

@app.get("/demographics")
async def demographics():
    return engine.demographics()


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    engine.clients.add(websocket)
    try:
        await websocket.send_json({"type": "snapshot", "data": engine.snapshot()})
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        engine.clients.discard(websocket)

