from fastapi import Request, WebSocket

from brewflow.payment_runtime import PaymentRuntime
from brewflow.queue_runtime import QueueRuntime


def runtime_from_request(request: Request) -> QueueRuntime:
    return request.app.state.queue_runtime


def runtime_from_websocket(websocket: WebSocket) -> QueueRuntime:
    return websocket.app.state.queue_runtime


def payment_runtime_from_request(request: Request) -> PaymentRuntime:
    return request.app.state.payment_runtime
