from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from brewflow.api.configuration import router as configuration_router
from brewflow.api.events import router as events_router
from brewflow.api.history import router as history_router
from brewflow.api.pages import create_pages_router
from brewflow.api.pos import router as pos_router
from brewflow.api.queue import router as queue_router
from brewflow.payment_runtime import PaymentRuntime
from brewflow.queue_runtime import QueueRuntime
from brewflow.settings import (
    CatalogSettings,
    DEFAULT_DATABASE_URI,
    DEFAULT_FRONTEND_DIST,
    PaymentSettings,
    QueueSettings,
    load_catalog_settings,
    load_payment_settings,
    load_queue_settings,
)


def create_app(
    *,
    database_uri: str = DEFAULT_DATABASE_URI,
    frontend_dist: Path = DEFAULT_FRONTEND_DIST,
    queue_settings: QueueSettings | None = None,
    catalog_settings: CatalogSettings | None = None,
    payment_settings: PaymentSettings | None = None,
    stripe_client=None,
) -> FastAPI:
    settings = queue_settings or load_queue_settings()
    catalog = catalog_settings or load_catalog_settings()
    payments = payment_settings or load_payment_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.queue_runtime = await QueueRuntime.create(database_uri, settings)
        try:
            app.state.payment_runtime = await PaymentRuntime.create(
                database_uri,
                app.state.queue_runtime,
                catalog,
                payments,
                stripe_client=stripe_client,
            )
            try:
                yield
            finally:
                await app.state.payment_runtime.close()
        finally:
            await app.state.queue_runtime.close()

    app = FastAPI(title="BrewFlow", lifespan=lifespan)
    app.include_router(queue_router)
    app.include_router(history_router)
    app.include_router(events_router)
    app.include_router(configuration_router)
    app.include_router(pos_router)
    app.include_router(create_pages_router(frontend_dist))

    assets = frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    return app
