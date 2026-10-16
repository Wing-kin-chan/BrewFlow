import asyncio

import pytest

from brewflow.events import QueueEvents


class Peer:
    def __init__(self, behavior: str = "good"):
        self.behavior = behavior
        self.messages: list[dict] = []
        self.sent = asyncio.Event()
        self.closed = False
        self.active_sends = 0
        self.max_active_sends = 0

    async def send_json(self, message: dict) -> None:
        self.active_sends += 1
        self.max_active_sends = max(self.max_active_sends, self.active_sends)
        try:
            if self.behavior == "slow":
                await asyncio.Event().wait()
            if self.behavior == "failed":
                raise RuntimeError("send failed")
            self.messages.append(message)
            self.sent.set()
            await asyncio.sleep(0)
        finally:
            self.active_sends -= 1

    async def close(self) -> None:
        self.closed = True


class HandshakePeer(Peer):
    def __init__(self, *, fail_connected: bool = False):
        super().__init__()
        self.fail_connected = fail_connected
        self.accepted = False
        self.connected_send_started = asyncio.Event()
        self.release_connected = asyncio.Event()

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        if message["type"] != "queue.connected":
            await super().send_json(message)
            return
        self.connected_send_started.set()
        if self.fail_connected:
            raise RuntimeError("handshake send failed")
        await self.release_connected.wait()
        self.messages.append(message)


@pytest.mark.asyncio
async def test_broadcast_sends_to_peers_concurrently_and_drops_slow_or_failed_peers():
    events = QueueEvents(send_timeout=0.05)
    good = Peer()
    slow = Peer("slow")
    failed = Peer("failed")
    events.connections.update({good, slow, failed})

    broadcast = asyncio.create_task(events.broadcast_change(1))
    await asyncio.wait_for(good.sent.wait(), timeout=0.2)
    assert not broadcast.done()
    await asyncio.wait_for(broadcast, timeout=0.5)

    assert good.messages == [{"type": "queue.changed", "revision": 1}]
    assert good in events.connections
    assert slow not in events.connections and slow.closed
    assert failed not in events.connections and failed.closed


@pytest.mark.asyncio
async def test_concurrent_broadcasts_are_serialized_and_stale_revisions_are_skipped():
    events = QueueEvents(send_timeout=0.1)
    peer = Peer()
    events.connections.add(peer)

    await asyncio.gather(
        events.broadcast_change(2),
        events.broadcast_change(1),
        events.broadcast_change(3),
    )

    assert [message["revision"] for message in peer.messages] == [2, 3]
    assert peer.max_active_sends == 1


@pytest.mark.asyncio
async def test_connect_registers_peer_and_serializes_connected_before_change():
    events = QueueEvents(send_timeout=0.5)
    peer = HandshakePeer()

    connect = asyncio.create_task(events.connect(peer, 7))
    await asyncio.wait_for(peer.connected_send_started.wait(), timeout=0.2)
    assert peer.accepted
    assert peer in events.connections

    broadcast = asyncio.create_task(events.broadcast_change(8))
    await asyncio.sleep(0)
    assert not broadcast.done()

    peer.release_connected.set()
    await asyncio.gather(connect, broadcast)

    assert peer.messages == [
        {"type": "queue.connected", "revision": 7},
        {"type": "queue.changed", "revision": 8},
    ]


@pytest.mark.asyncio
async def test_connect_send_failure_closes_peer_and_releases_broadcast_lock():
    events = QueueEvents(send_timeout=0.1)
    failed = HandshakePeer(fail_connected=True)

    with pytest.raises(RuntimeError, match="handshake send failed"):
        await events.connect(failed, 0)

    assert failed not in events.connections
    assert failed.closed

    good = Peer()
    events.connections.add(good)
    await asyncio.wait_for(events.broadcast_change(1), timeout=0.2)
    assert good.messages == [{"type": "queue.changed", "revision": 1}]


@pytest.mark.asyncio
async def test_connect_timeout_and_cancellation_both_clean_up_registered_peer():
    timed_events = QueueEvents(send_timeout=0.02)
    timed_out = HandshakePeer()
    with pytest.raises(TimeoutError):
        await timed_events.connect(timed_out, 0)
    assert timed_out not in timed_events.connections
    assert timed_out.closed

    cancelled_events = QueueEvents(send_timeout=0.1)
    cancelled = HandshakePeer()
    connect = asyncio.create_task(cancelled_events.connect(cancelled, 0))
    await asyncio.wait_for(cancelled.connected_send_started.wait(), timeout=0.2)
    connect.cancel()
    with pytest.raises(asyncio.CancelledError):
        await connect
    assert cancelled not in cancelled_events.connections
    assert cancelled.closed
