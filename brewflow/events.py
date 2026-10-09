import asyncio

from fastapi import WebSocket


class QueueEvents:
    def __init__(self, *, send_timeout: float = 1.0) -> None:
        self.connections: set[WebSocket] = set()
        self.send_timeout = send_timeout
        self._broadcast_lock = asyncio.Lock()
        self._last_revision = -1

    async def connect(self, websocket: WebSocket, revision: int) -> None:
        async with self._broadcast_lock:
            try:
                await websocket.accept()
                self.connections.add(websocket)
                await asyncio.wait_for(
                    websocket.send_json(
                        {"type": "queue.connected", "revision": revision}
                    ),
                    timeout=self.send_timeout,
                )
            except asyncio.CancelledError:
                self.disconnect(websocket)
                try:
                    await asyncio.wait_for(
                        websocket.close(), timeout=self.send_timeout
                    )
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                raise
            except Exception:
                await self._drop(websocket)
                raise

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def _drop(self, connection: WebSocket) -> None:
        self.disconnect(connection)
        try:
            await asyncio.wait_for(connection.close(), timeout=self.send_timeout)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    async def _send(self, connection: WebSocket, revision: int) -> None:
        try:
            await asyncio.wait_for(
                connection.send_json(
                    {"type": "queue.changed", "revision": revision}
                ),
                timeout=self.send_timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await self._drop(connection)

    async def broadcast_change(self, revision: int) -> None:
        async with self._broadcast_lock:
            if revision <= self._last_revision:
                return
            await asyncio.gather(
                *(self._send(connection, revision) for connection in tuple(self.connections))
            )
            self._last_revision = revision
