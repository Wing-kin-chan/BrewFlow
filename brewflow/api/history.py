from fastapi import APIRouter, Depends

from brewflow.api.dependencies import runtime_from_request
from brewflow.domain.queue import HistorySnapshot
from brewflow.queue_runtime import QueueRuntime


router = APIRouter()


@router.get("/api/history/orders", response_model=HistorySnapshot)
async def history_orders(
    runtime: QueueRuntime = Depends(runtime_from_request),
) -> HistorySnapshot:
    return await runtime.history_snapshot()
