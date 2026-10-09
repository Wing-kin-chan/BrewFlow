# BrewFlow

BrewFlow runs as one FastAPI process and serves a Vue frontend. Stage 1 provides the live Queue
and Order History pages only.

## Development

```text
uv sync
npm --prefix frontend install
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

The Vite development server proxies queue data and WebSocket routes to FastAPI at
`127.0.0.1:8000`. Open the Vite URL and navigate to `/api/queue`.

## Production-style local run

```text
npm --prefix frontend run build
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

FastAPI serves the compiled frontend at `/api/queue` and `/api/history`; `/` redirects to the
queue. The default SQLite database remains under `brewflow/data/` and is ignored by Git.

## Current static queue settings

Configuration UI and account settings are intentionally deferred. Queue search depth and batch
capacity currently come from `brewflow/config/config.json`. The legacy drink volumes and the
capacity value use the existing numeric scale; they must be converted together to real
millilitres when approved configuration data is introduced. No database schema was changed for
Stage 1.

## Packaging scope

Stage 1 is run from a source checkout after building `frontend/dist`. The Python wheel does not
bundle the root `main.py` entry point or compiled frontend and is not a standalone deployment
artifact.
