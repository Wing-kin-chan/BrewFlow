from fastapi import Request, WebSocket

from brewflow.queue_runtime import QueueRuntime


def runtime_from_request(request: Request) -> QueueRuntime:
    return request.app.state.queue_runtime


def runtime_from_websocket(websocket: WebSocket) -> QueueRuntime:
    return websocket.app.state.queue_runtime
