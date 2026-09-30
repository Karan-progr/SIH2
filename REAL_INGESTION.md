# Authorized Production Ingestion

The production entrypoint is separate from the synthetic demo entrypoint:

```bash
cd backend
cp ../.env.example .env
export ENABLE_REAL_INGESTION=true
export PIPELINE_DATABASE_URL=sqlite:///data/sentinelx.db
.venv/bin/uvicorn app.real_main:app --host 0.0.0.0 --port 8000
```

For Docker, build `backend/Dockerfile.real` instead of the demo Dockerfile.

## X API v2

Set `X_BEARER_TOKEN` and optionally `X_QUERY`. The collector calls the official X API v2 recent-search endpoint with `tweet.fields=created_at,public_metrics,author_id,lang,entities`. It does not scrape HTML. The X developer account must have access to recent search and must comply with X's terms and retention rules.

## Telegram Bot API

Set `TELEGRAM_BOT_TOKEN`. The bot must be added to the target group/channel with appropriate permission to receive posts. The collector uses `getUpdates` long polling for `message`, `channel_post`, and `edited_channel_post`, with a 25-second server-side timeout and a 60-second ingestion loop.

The Bot API cannot read arbitrary Telegram history or channels the bot cannot access. For authorized public-channel monitoring that requires historical reads, use a separately approved MTProto client with `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, a stored session, and explicit channel allowlisting. Do not use user-account sessions without authorization.

## Pipeline

Every authorized event is normalized, hashed at the author identifier boundary, deduplicated by `(platform, platform_post_id)`, persisted with its raw source payload, and analyzed. The ML pipeline loads a Hugging Face sentiment classifier and a sentence-transformers embedding model when available. It stores sentiment, confidence, emotion, keywords, model version, and normalized embeddings. If model loading fails, it records the configured model version and uses a transparent lexical fallback; this is observable in logs and should be treated as degraded mode in production.

Endpoints:

- `GET /health`
- `GET /sources`
- `GET /events`
- `POST /ingestion/poll`
- `WS /ws/live`

This path is intentionally separate from the offline dashboard until the dashboard is migrated to the persistent production API. The old `/` API remains the clearly labeled synthetic demo.
