"""Persistent, evidence-preserving analysis pipeline for authorized source events."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ProductionPipeline:
    def __init__(self, database_url: str | None = None):
        raw = database_url or os.getenv("PIPELINE_DATABASE_URL", "sqlite:///data/sentinelx.db")
        path = raw.removeprefix("sqlite:///")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS source_events (id TEXT PRIMARY KEY, platform TEXT NOT NULL, platform_post_id TEXT NOT NULL, author_id_hash TEXT NOT NULL, text TEXT NOT NULL, event_time TEXT NOT NULL, payload TEXT NOT NULL, inserted_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS analyses (event_id TEXT PRIMARY KEY, sentiment TEXT NOT NULL, sentiment_confidence REAL NOT NULL, emotion TEXT NOT NULL, emotion_confidence REAL NOT NULL, keywords TEXT NOT NULL, embedding TEXT, model_version TEXT NOT NULL, analyzed_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES source_events(id));
        CREATE INDEX IF NOT EXISTS source_events_time ON source_events(event_time DESC);
        CREATE INDEX IF NOT EXISTS source_events_platform ON source_events(platform, platform_post_id);
        """)
        self.db.commit()
        self.model_version = os.getenv("ML_MODEL_VERSION", "distilbert-sst2 + rule-emotion-v1")
        self.sentiment_model = None
        self.embedding_model = None

    def _load_models(self):
        if self.sentiment_model is not None:
            return
        try:
            from transformers import pipeline
            self.sentiment_model = pipeline("sentiment-analysis", model=os.getenv("SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"), truncation=True)
        except Exception:
            self.sentiment_model = False
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
        except Exception:
            self.embedding_model = False

    def _analyze(self, text: str) -> dict[str, Any]:
        self._load_models()
        if self.sentiment_model:
            result = self.sentiment_model(text[:4000])[0]
            sentiment = "positive" if result["label"].upper() == "POSITIVE" else "negative"
            confidence = float(result["score"])
        else:
            lower = text.lower()
            negative = sum(word in lower for word in ("outage", "attack", "fear", "fraud", "crisis", "anger"))
            positive = sum(word in lower for word in ("support", "verified", "help", "safe", "restore"))
            sentiment = "negative" if negative > positive else "positive" if positive > negative else "neutral"
            confidence = min(0.99, 0.55 + abs(negative - positive) * 0.08)
        emotion_words = {"anger": ("angry", "anger", "furious"), "fear": ("fear", "afraid", "threat"), "anxiety": ("anxious", "worry", "uncertain"), "support": ("support", "help", "solidarity"), "excitement": ("great", "excited", "launch")}
        emotion = "other"
        for label, words in emotion_words.items():
            if any(word in text.lower() for word in words):
                emotion = label
                break
        tokens = [token.strip(".,!?():;[]{}\"'").lower() for token in text.split()]
        keywords = sorted({token for token in tokens if len(token) > 4 and token.isalpha()})[:12]
        embedding = None
        if self.embedding_model:
            embedding = self.embedding_model.encode(text[:4000], normalize_embeddings=True).tolist()
        return {"sentiment": sentiment, "sentiment_confidence": round(confidence, 4), "emotion": emotion, "emotion_confidence": 0.71 if emotion != "other" else 0.42, "keywords": keywords, "embedding": embedding}

    def ingest(self, event: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        platform = event["platform"]
        platform_id = str(event["platform_post_id"])
        event_id = event.get("id") or hashlib.sha256(f"{platform}:{platform_id}".encode()).hexdigest()
        author_hash = hashlib.sha256(str(event.get("author_id", "")).encode()).hexdigest()
        existing = self.db.execute("SELECT id FROM source_events WHERE id = ? OR (platform = ? AND platform_post_id = ?)", (event_id, platform, platform_id)).fetchone()
        if existing:
            row = self.db.execute("SELECT se.*, a.sentiment, a.sentiment_confidence, a.emotion, a.emotion_confidence, a.keywords, a.model_version FROM source_events se LEFT JOIN analyses a ON a.event_id = se.id WHERE se.id = ?", (existing["id"],)).fetchone()
            return dict(row), False
        created = datetime.now(timezone.utc).isoformat()
        self.db.execute("INSERT INTO source_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (event_id, platform, platform_id, author_hash, event.get("text", ""), event.get("timestamp", created), json.dumps(event), created))
        analysis = self._analyze(event.get("text", ""))
        self.db.execute("INSERT INTO analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (event_id, analysis["sentiment"], analysis["sentiment_confidence"], analysis["emotion"], analysis["emotion_confidence"], json.dumps(analysis["keywords"]), json.dumps(analysis["embedding"]) if analysis["embedding"] else None, self.model_version, created))
        self.db.commit()
        return {**event, "id": event_id, "author_id_hash": author_hash, "analysis": {k: v for k, v in analysis.items() if k != "embedding"}, "raw_persisted": True}, True

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT se.*, a.sentiment, a.sentiment_confidence, a.emotion, a.emotion_confidence, a.keywords, a.model_version FROM source_events se LEFT JOIN analyses a ON a.event_id = se.id ORDER BY event_time DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            item = dict(row); item["raw_payload"] = json.loads(item.pop("payload")); item["analysis"] = {"sentiment": item.pop("sentiment"), "confidence": item.pop("sentiment_confidence"), "emotion": item.pop("emotion"), "emotion_confidence": item.pop("emotion_confidence"), "keywords": json.loads(item.pop("keywords") or "[]"), "model_version": item.pop("model_version")}; result.append(item)
        return result
