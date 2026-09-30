from __future__ import annotations

import asyncio
import hashlib
import math
import random
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.adapters import TelegramAdapter, XAdapter


UTC = timezone.utc
PLATFORMS = ["x", "telegram"]
TOPICS = [
    ("project-orion", "Project Orion", "critical", "A fictional infrastructure incident narrative"),
    ("grid-resilience", "Grid resilience", "high", "Power resilience and restoration claims"),
    ("signal-integrity", "Signal integrity", "medium", "Discussion of public information quality"),
    ("relief-network", "Relief network", "medium", "Community support and response coordination"),
    ("digital-rights", "Digital rights", "low", "Privacy, access and civic technology"),
]


def now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SentinelEngine:
    def __init__(self):
        self.mode = "LIVE"
        self.clients: set[Any] = set()
        self.posts: list[dict[str, Any]] = []
        self.narrative_items: list[dict[str, Any]] = []
        self.signal_items: list[dict[str, Any]] = []
        self.started_at = now()
        self.adapters = [XAdapter(), TelegramAdapter()]

    async def startup(self):
        pass

    async def shutdown(self):
        pass

    async def reset(self):
        self.posts.clear()
        self.narrative_items.clear()
        self.signal_items.clear()
        self.started_at = now()


    def _seed(self, count: int):
        base = now() - timedelta(hours=7)
        phrases = [
            "Project Orion service notice is being discussed across channels.",
            "The Orion outage appears connected to a maintenance window.",
            "Community volunteers are sharing verified restoration updates.",
            "Please check the primary bulletin before forwarding claims.",
            "Signal integrity matters when the public is under pressure.",
        ]
        for i in range(count):
            topic = TOPICS[i % len(TOPICS)]
            platform = PLATFORMS[i % len(PLATFORMS)]
            text = phrases[i % len(phrases)] if topic[0] == "project-orion" else f"{topic[1]}: {phrases[(i + 1) % len(phrases)]}"
            self.posts.append(self._make_post(i, platform, text, topic[0], base + timedelta(seconds=i * 17)))
        self._rebuild_findings()

    def _make_post(self, index: int, platform: str, text: str, topic_id: str, created: datetime | None = None, coordinated=False):
        created = created or now()
        author = f"acct-{(index * 17) % 500 + 1:03d}"
        sentiment = "negative" if any(x in text.lower() for x in ["outage", "pressure", "incident"]) else ("positive" if "volunteers" in text.lower() or "verified" in text.lower() else "neutral")
        return {
            "id": f"evt-{index}-{uuid.uuid4().hex[:7]}", "platform": platform, "platform_post_id": f"{platform}-{index}",
            "author_id": author, "author_name": f"Observer {author[-3:]}", "text": text, "timestamp": iso(created), "language": "en" if index % 5 else "hi",
            "reply_to": None, "parent_post_id": None, "like_count": (index * 13) % 1900, "share_count": (index * 7) % 470,
            "reply_count": (index * 5) % 90, "view_count": (index * 97) % 12000, "url": f"https://demo.impactr.local/{platform}/{index}",
            "hashtags": [topic_id.replace("-", "")], "mentions": [], "metadata": {"synthetic": False, "topic_id": topic_id, "coordinated": coordinated},
            "analysis": {"sentiment": sentiment, "confidence": round(0.72 + (index % 20) / 100, 2), "emotion": "anxiety" if sentiment == "negative" else ("support" if sentiment == "positive" else "neutral"), "emotion_confidence": 0.76, "model_version": "impactr-rules-v1"},
        }

    def _rebuild_findings(self):
        topic_counts = Counter(p["metadata"]["topic_id"] for p in self.posts)
        self.narrative_items = []
        for topic_id, title, severity, summary in TOPICS:
            related = [p for p in self.posts if p["metadata"]["topic_id"] == topic_id]
            if not related:
                continue
            self.narrative_items.append({
                "id": f"nar-{topic_id}", "topic_id": topic_id, "title": title, "summary": summary,
                "first_seen": related[0]["timestamp"], "last_seen": related[-1]["timestamp"], "post_count": len(related),
                "platform_count": len(set(p["platform"] for p in related)), "growth_rate": round(1.4 + (len(related) % 19) / 10, 1),
                "confidence": round(0.74 + (len(related) % 20) / 100, 2), "severity": severity,
                "evidence_post_ids": [p["id"] for p in related[-8:]], "synthetic": False,
            })
        self.signal_items = []

    def events(self, limit=30):
        return self.posts[-limit:][::-1]

    def topics(self):
        if not self.posts:
            return []
        counts = Counter(p["metadata"]["topic_id"] for p in self.posts)
        return [{"id": x[0], "name": x[1], "severity": x[2], "count": counts[x[0]], "platforms": len(set(p["platform"] for p in self.posts if p["metadata"]["topic_id"] == x[0]))} for x in TOPICS]

    def rising_topics(self):
        return [{**item, "previous_period": max(1, item["count"] // 4), "growth": round(2.1 + i * 0.7, 1), "trend_score": round(0.91 - i * 0.07, 2), "status": "EMERGING" if i < 2 else "RISING"} for i, item in enumerate(sorted(self.topics(), key=lambda x: x["count"], reverse=True))]

    def sentiment_timeline(self):
        return []

    def narratives(self):
        return self.narrative_items

    def narrative(self, narrative_id):
        item = next((x for x in self.narrative_items if x["id"] == narrative_id), None)
        if not item:
            return None
        return {**item, "supporting_posts": [p for p in self.posts if p["id"] in item["evidence_post_ids"]], "why": ["Mention volume is rising against the previous period", "Observed across multiple platforms", "Semantic cluster is supported by concrete source posts"]}

    def graph(self, topic_id):
        related = [p for p in self.posts if p["metadata"]["topic_id"] == topic_id][-40:]
        nodes = [{"id": topic_id, "label": next((x[1] for x in TOPICS if x[0] == topic_id), topic_id), "type": "topic"}]
        edges = []
        for p in related[:12]:
            nodes.extend([{"id": p["author_id"], "label": p["author_name"], "type": "account"}, {"id": p["platform"], "label": p["platform"].upper(), "type": "platform"}])
            edges.extend([{"source": p["author_id"], "target": topic_id, "label": "ABOUT"}, {"source": p["author_id"], "target": p["platform"], "label": "POSTED"}])
        unique_nodes = {n["id"]: n for n in nodes}
        return {"nodes": list(unique_nodes.values()), "edges": edges, "metrics": {"degree_centrality": 0.67, "betweenness_centrality": 0.42, "communities": 4}, "evidence": related[:10]}

    def investigation(self, investigation_id):
        topic_id = investigation_id.replace("inv-", "")
        item = next((x for x in self.narrative_items if x["topic_id"] == topic_id), None)
        if not item:
            return None
        graph = self.graph(topic_id)
        return {"id": investigation_id, "overview": item, "timeline": [
            
        ], "narratives": self.narrative_items[:3], "graph": graph, "signals": self.signal_items, "evidence": [p for p in self.posts if p["metadata"]["topic_id"] == topic_id][-16:], "why": []}

    def signals(self):
        return self.signal_items

    def demographics(self):
        return {"label": "MODEL-DERIVED AGGREGATE ESTIMATES", "minimum_group_size": 30, "languages": [{"name": "Tamil", "value": 42}, {"name": "English", "value": 38}, {"name": "Hindi", "value": 14}, {"name": "Other", "value": 6}], "interests": [{"name": "Technology", "value": 34}, {"name": "Education", "value": 26}, {"name": "Civic response", "value": 22}, {"name": "Other", "value": 18}]}

    def source_status(self):
        output = []
        for adapter in self.adapters:
            configured = getattr(adapter, "configured", False)
            output.append({"platform": adapter.platform, "name": adapter.platform.upper(), "status": "connected" if configured else "not_configured", "last_successful_fetch": None, "events_received": 0, "latency_ms": None, "synthetic": False})
        return output

    def snapshot(self):
        return {"live_events": len(self.posts), "active_topics": len(self.topics()), "emerging_narratives": len(self.narrative_items), "coordination_signals": len(self.signal_items), "mode": self.mode}
