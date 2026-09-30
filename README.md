# ImpactR

ImpactR is an evidence-first social intelligence prototype for SIH26152, Social Media Analytics. It is designed around a simple trust boundary: observed source events, model-derived findings, anomaly signals, and supporting evidence are displayed as different things.

## Implemented

- FastAPI REST API and `/ws/live` WebSocket.
- Common adapters for X, Telegram, Reddit, YouTube, and `DemoDataAdapter`.
- Normalized social event shape with source metadata and model result metadata.
- Synthetic seed corpus of 5,000 posts, 500 demo accounts, 5 topics, multiple platforms and languages.
- Explainable narrative clustering, trend score fields, sentiment/emotion results, propagation graph payload, behavioral coordination signal, aggregate demographic estimates, and investigation endpoint.
- Next.js analyst board with live activity feed, trend ranking, sentiment chart, emotion view, signal evidence, source health, and incident investigation page.
- PostgreSQL schema with tables for posts, comments, topics, mentions, NLP results, embeddings, graph relationships, trends, narratives, signals, investigations, demographics, and system events.
- Docker Compose services for frontend, backend, PostgreSQL, and Redis.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:3000. The API is at http://localhost:8000/docs.

The backend currently keeps the demo corpus in-process for a low-friction prototype run. PostgreSQL and Redis are provisioned and the normalized production schema is included in `database/schema.sql`; the service boundaries are ready for persistence and worker extraction as the prototype moves to production.

## Run without Docker

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Demo flow

1. Open the board and confirm the `SIMULATION` and `LIVE` labels.
2. Click `Start simulation`; use `1x`, `5x`, or `20x` speed.
3. Watch the live event feed grow and counters update through WebSocket.
4. Select `Open full investigation` on Project Orion.
5. Review first detection, cross-platform propagation, narrative map, coordination signal, and actual supporting synthetic events.
6. Use `Reset` to return to the seeded 5,000-event state.

## Environment and real sources

Set credentials only in `.env`, never in source. The X adapter expects `X_BEARER_TOKEN` and is intended for the official authorized X API. Telegram expects `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_BOT_TOKEN`. Reddit and YouTube variables are included for their official APIs.

`GET /sources` reports `not_configured` for blank credentials. It never presents a disconnected source as connected. A real ingestion worker should call the adapter's authorized API, normalize the payload, persist raw and normalized records, then invoke the analysis pipeline.

## Transparent analysis rules

Trend score is documented as: `normalized velocity * .35 + normalized acceleration * .25 + normalized engagement * .20 + cross-platform factor * .20`. The UI uses neutral terms such as “high network centrality” and “potential coordinated behavior”. A behavioral anomaly is not a bot determination. Demographics are aggregate estimates only and require a minimum group size.

The current prototype's `impactr-rules-v1` analysis metadata is intentionally explicit. Replacing it with sentence-transformers, Hugging Face classifiers, pgvector nearest-neighbor search, NetworkX, and Celery workers is the next production slice; the database schema already has storage boundaries for these outputs.

## Tests

```bash
cd backend
pytest
```

The focused tests cover synthetic seeding, traceable narrative evidence, and evidence-first coordination output. API smoke tests can be run after the service starts with the OpenAPI page or `curl http://localhost:8000/health`.

## Privacy and ethics

Use only lawfully obtained, authorized public or partner data. Store hashed identifiers where identity is not operationally required, minimize raw payload retention, enforce role-based access before deployment, and log analyst access. Model outputs are leads for review, not facts. Do not use the platform to infer or expose individual sensitive demographics.

## Three-minute SIH presentation script

**0:00–0:25:** “ImpactR is an evidence-first social intelligence board. Notice the explicit SIMULATION label and source-health state: no disconnected API is being faked.”

**0:25–1:05:** Start Project Orion at 5x. Point out the WebSocket-updated events, cross-platform topic ranking, trend formula, and sentiment shift. Explain that “emerging” means velocity and cross-platform change, not simply a large count.

**1:05–1:55:** Open the investigation. Walk through first detection, the temporal propagation graph, narrative clusters, and the “why this result” observable features.

**1:55–2:30:** Open the coordination signal. Show 27 accounts, 91% median semantic similarity, 43 seconds, and shared URLs. Emphasize the wording: potential coordinated behavior, not “bots”. Open supporting posts to prove traceability.

**2:30–3:00:** Return to the board, pause/reset the simulation, then show source health and explain how authorized X/Telegram adapters slot into the same normalized pipeline.

## Strongest differentiators

1. Every major finding is paired with observable features and source events.
2. The offline demo is genuinely interactive and visibly labeled synthetic.
3. Cross-platform narratives are modeled separately from keyword-level topics.
4. Coordination analysis is framed as a reviewable anomaly signal rather than an unsupported accusation.
5. The schema and adapters make the prototype extensible toward PostgreSQL/pgvector, Redis workers, NetworkX, and eventually Neo4j.

## Future work

Complete official API fetch/stream implementations, move analysis into Celery workers, persist the demo and live corpus in PostgreSQL, add pgvector embeddings and multilingual transformer models, add analyst authentication/RBAC, and expand temporal graph playback with evidence-level edge inspection.
