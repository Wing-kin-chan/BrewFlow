from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from brewflow.api.events import router as events_router
from brewflow.api.history import router as history_router
from brewflow.api.pages import create_pages_router
from brewflow.api.queue import router as queue_router
from brewflow.queue_runtime import QueueRuntime
from brewflow.settings import (
    DEFAULT_DATABASE_URI,
    DEFAULT_FRONTEND_DIST,
    QueueSettings,
    load_queue_settings,
)


def create_app(
    *,
    database_uri: str = DEFAULT_DATABASE_URI,
    frontend_dist: Path = DEFAULT_FRONTEND_DIST,
    queue_settings: QueueSettings | None = None,
) -> FastAPI:
    settings = queue_settings or load_queue_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.queue_runtime = await QueueRuntime.create(database_uri, settings)
        try:
            yield
        finally:
            await app.state.queue_runtime.close()

    app = FastAPI(title="BrewFlow", lifespan=lifespan)
    app.include_router(queue_router)
    app.include_router(history_router)
    app.include_router(events_router)
    app.include_router(create_pages_router(frontend_dist))

    assets = frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    return app
