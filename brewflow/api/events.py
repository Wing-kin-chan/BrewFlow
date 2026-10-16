from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from brewflow.api.dependencies import runtime_from_websocket


router = APIRouter()


@router.websocket("/api/queue/events")
async def queue_events(websocket: WebSocket) -> None:
    runtime = runtime_from_websocket(websocket)
    await runtime.events.connect(websocket, runtime.revision)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        runtime.events.disconnect(websocket)
