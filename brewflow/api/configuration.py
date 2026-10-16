from fastapi import APIRouter, Depends, HTTPException

from brewflow.api.dependencies import payment_runtime_from_request
from brewflow.domain.pos import DemoModeResponse, DemoModeUpdate
from brewflow.payment_runtime import DemoModeNotAllowedError, PaymentRuntime


router = APIRouter()


@router.get("/api/configuration/demo-mode", response_model=DemoModeResponse)
async def demo_mode(
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> DemoModeResponse:
    return await runtime.configuration()


@router.put("/api/configuration/demo-mode", response_model=DemoModeResponse)
async def update_demo_mode(
    update: DemoModeUpdate,
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> DemoModeResponse:
    try:
        return await runtime.set_demo_mode(update.demoModeEnabled)
    except DemoModeNotAllowedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
