from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from brewflow.api.dependencies import runtime_from_request
from brewflow.domain.models import Order
from brewflow.domain.queue import QueueSnapshot
from brewflow.queue_runtime import (
    IntakeConflictError,
    InvalidOrderValueError,
    QueueRuntime,
)


router = APIRouter()


class CompletionRequest(BaseModel):
    drinkIDs: list[str] = Field(default_factory=list)


class IntakeResponse(BaseModel):
    status: Literal["accepted", "duplicate"]
    orderID: str
    queue: QueueSnapshot


@router.get("/api/queue/state", response_model=QueueSnapshot)
async def queue_state(
    runtime: QueueRuntime = Depends(runtime_from_request),
) -> QueueSnapshot:
    return await runtime.queue_snapshot()


@router.post(
    "/api/queue/orders",
    response_model=IntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_order(
    order: Order,
    runtime: QueueRuntime = Depends(runtime_from_request),
) -> IntakeResponse:
    try:
        intake_status, snapshot = await runtime.intake(order)
    except InvalidOrderValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except IntakeConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return IntakeResponse(status=intake_status, orderID=order.orderID, queue=snapshot)


@router.post("/api/queue/completions", response_model=QueueSnapshot)
async def complete_drinks(
    completion: CompletionRequest,
    runtime: QueueRuntime = Depends(runtime_from_request),
) -> QueueSnapshot:
    return await runtime.complete(set(completion.drinkIDs))
