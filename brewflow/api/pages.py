from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse


def create_pages_router(frontend_dist: Path) -> APIRouter:
    router = APIRouter()
    index_file = frontend_dist / "index.html"

    def frontend_page() -> FileResponse:
        if not index_file.is_file():
            raise HTTPException(
                status_code=503,
                detail="Frontend build not found. Run `npm --prefix frontend run build`.",
            )
        return FileResponse(index_file)

    @router.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/api/queue")

    @router.get("/api/queue", include_in_schema=False)
    async def queue_page() -> FileResponse:
        return frontend_page()

    @router.get("/api/history", include_in_schema=False)
    async def history_page() -> FileResponse:
        return frontend_page()

    return router
