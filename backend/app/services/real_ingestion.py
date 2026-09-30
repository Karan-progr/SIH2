"""Authorized social ingestion helpers. HTML scraping is intentionally unsupported."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx


def normalized(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"{platform}:{payload.get('id', '')}",
        "platform": platform,
        "platform_post_id": str(payload.get("id", "")),
        "author_id": str(payload.get("author_id", "")),
        "author_name": payload.get("author_name", ""),
        "text": payload.get("text", ""),
        "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "language": payload.get("language", "und"),
        "reply_to": payload.get("reply_to"),
        "parent_post_id": payload.get("parent_post_id"),
        "like_count": payload.get("like_count", 0),
        "share_count": payload.get("share_count", 0),
        "reply_count": payload.get("reply_count", 0),
        "view_count": payload.get("view_count", 0),
        "url": payload.get("url", ""),
        "hashtags": payload.get("hashtags", []),
        "mentions": payload.get("mentions", []),
        "metadata": payload.get("metadata", {}),
    }


async def fetch_x_recent(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch X API v2 recent search results using an authorized bearer token."""
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        return []
    params = {"query": os.getenv("X_QUERY", "lang:en -is:retweet"), "max_results": max(10, min(limit, 100)), "tweet.fields": "created_at,public_metrics,author_id,lang,entities"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://api.x.com/2/tweets/search/recent", params=params, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        body = response.json()
    result = []
    for item in body.get("data", []):
        metrics = item.get("public_metrics", {})
        result.append(normalized("x", {"id": item["id"], "author_id": item.get("author_id", ""), "text": item.get("text", ""), "timestamp": item.get("created_at"), "language": item.get("lang", "und"), "like_count": metrics.get("like_count", 0), "share_count": metrics.get("retweet_count", 0), "reply_count": metrics.get("reply_count", 0), "view_count": metrics.get("impression_count", 0), "metadata": {"entities": item.get("entities", {}), "raw_source": "x_api_v2"}}))
    return result


async def fetch_telegram_updates(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch Bot API updates. The bot must be a member/admin of the target channels."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return []
    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"limit": min(limit, 100), "timeout": 25, "allowed_updates": '["message","channel_post","edited_channel_post"]'})
        response.raise_for_status()
        body = response.json()
    result = []
    for update in body.get("result", []):
        message = update.get("channel_post") or update.get("edited_channel_post") or update.get("message")
        if not message or not message.get("text"):
            continue
        sender = message.get("from", {})
        result.append(normalized("telegram", {"id": message.get("message_id", update.get("update_id")), "author_id": sender.get("id", message.get("chat", {}).get("id", "")), "author_name": sender.get("username", message.get("chat", {}).get("title", "")), "text": message["text"], "timestamp": datetime.fromtimestamp(message.get("date", 0), timezone.utc).isoformat(), "metadata": {"chat_id": message.get("chat", {}).get("id"), "raw_source": "telegram_bot_api"}}))
    return result
