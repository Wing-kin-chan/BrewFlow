from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, status

from brewflow.api.dependencies import payment_runtime_from_request
from brewflow.domain.pos import (
    CatalogResponse,
    CheckoutResponse,
    PosOrderInput,
    ReceiptResponse,
)
from brewflow.payment_runtime import (
    DemoModeNotAllowedError,
    DemoPaymentError,
    InvalidPosOrderError,
    PaymentNotConfiguredError,
    PaymentProviderError,
    PaymentRuntime,
    PaymentVerificationError,
    PosConflictError,
)


MAX_WEBHOOK_BYTES = 1_048_576
router = APIRouter()


@router.get("/api/pos/catalog", response_model=CatalogResponse)
async def catalog(
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> CatalogResponse:
    return runtime.catalog_response()


@router.post(
    "/api/pos/orders",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pos_order(
    order: PosOrderInput,
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> CheckoutResponse:
    try:
        return await runtime.create_checkout(order)
    except InvalidPosOrderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PosConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except PaymentNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except PaymentProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get(
    "/api/pos/receipts/{session_id}", response_model=ReceiptResponse
)
async def receipt(
    session_id: str = Path(
        min_length=1, max_length=255, pattern=r"^cs_[A-Za-z0-9_]+$"
    ),
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> ReceiptResponse:
    result = await runtime.receipt(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return result


@router.get(
    "/api/pos/demo-receipts/{order_id}", response_model=ReceiptResponse
)
async def demo_receipt(
    order_id: UUID = Path(),
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> ReceiptResponse:
    result = await runtime.demo_receipt(str(order_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return result


@router.post(
    "/api/pos/orders/{order_id}/demo-payment", response_model=ReceiptResponse
)
async def submit_demo_payment(
    order_id: UUID = Path(),
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> ReceiptResponse:
    try:
        return await runtime.submit_demo_payment(str(order_id))
    except DemoModeNotAllowedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DemoPaymentError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/api/payments/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    runtime: PaymentRuntime = Depends(payment_runtime_from_request),
) -> dict[str, str]:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            parsed_length = int(content_length)
            if parsed_length < 0:
                raise ValueError
            if parsed_length > MAX_WEBHOOK_BYTES:
                raise HTTPException(status_code=413, detail="Webhook body too large")
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid content length") from error
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Webhook body too large")
        payload.extend(chunk)
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    try:
        event = runtime.construct_webhook_event(bytes(payload), stripe_signature)
        await runtime.handle_webhook_event(event)
    except PaymentVerificationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PaymentNotConfiguredError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except PaymentProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "received"}
