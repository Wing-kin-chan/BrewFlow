from datetime import datetime

import pytest

from brewflow.domain.queue import Queue
from brewflow.queue_runtime import IntakeConflictError, InvalidOrderValueError, QueueRuntime
from tests.conftest import make_order


@pytest.mark.asyncio
async def test_intake_is_timestamped_idempotent_and_conflicts_are_rejected(tmp_path, queue_settings):
    now = datetime(2026, 2, 3, 9, 30)
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
        queue_settings,
        now=lambda: now,
    )
    order = make_order("order-1")
    try:
        result, snapshot = await runtime.intake(order)
        duplicate, duplicate_snapshot = await runtime.intake(order)
        stored = await runtime.store.get_order("order-1")

        assert result == "accepted"
        assert duplicate == "duplicate"
        assert snapshot.totalDrinks == duplicate_snapshot.totalDrinks == 1
        assert stored is not None
        assert stored.dateReceived == now.date()
        assert stored.timeReceived == now.time()
        assert stored.drinks[0].timeReceived == now.time()
        assert order.dateReceived != now.date()
        assert order.timeReceived != now.time()
        assert order.drinks[0].timeReceived == order.timeReceived

        conflicting = make_order("order-1", customer="Different")
        with pytest.raises(IntakeConflictError):
            await runtime.intake(conflicting)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_unknown_milk_is_rejected_without_persistence(tmp_path, queue_settings):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'milk.db'}", queue_settings
    )
    unknown = make_order(
        "order-1",
        [{"identifier": "drink", "drink": "Latte", "milk": "Unknown", "milk_volume": 2, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []}],
    )
    try:
        with pytest.raises(InvalidOrderValueError):
            await runtime.intake(unknown)
        assert await runtime.store.get_order("order-1") is None
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_restart_reconstructs_pending_queue_and_history(tmp_path, queue_settings):
    uri = f"sqlite+aiosqlite:///{tmp_path / 'restart.db'}"
    now = datetime.now().replace(microsecond=0)
    first = await QueueRuntime.create(uri, queue_settings, now=lambda: now)
    await first.intake(make_order("order-1"))
    await first.intake(make_order("order-2"))
    await first.complete({"order-1-drink-1"})
    await first.close()

    restarted = await QueueRuntime.create(uri, queue_settings, now=lambda: now)
    try:
        queue = await restarted.queue_snapshot()
        history = await restarted.history_snapshot()
        assert queue.totalOrders == 1
        assert queue.totalDrinks == 1
        assert history.totalOrders == 1
        assert history.totalDrinks == 1
    finally:
        await restarted.close()


@pytest.mark.asyncio
async def test_persistence_failure_does_not_mutate_memory(tmp_path, queue_settings, monkeypatch):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'failure.db'}", queue_settings
    )

    async def fail(_order):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(runtime.store, "add_order", fail)
    try:
        with pytest.raises(RuntimeError):
            await runtime.intake(make_order("order-1"))
        assert (await runtime.queue_snapshot()).totalDrinks == 0
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_completion_persistence_failure_does_not_mutate_memory(
    tmp_path, queue_settings, monkeypatch
):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'completion-failure.db'}", queue_settings
    )
    await runtime.intake(make_order("order-1"))

    async def fail(_identifiers, _completed_at):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(runtime.store, "complete_drinks", fail)
    try:
        with pytest.raises(RuntimeError):
            await runtime.complete({"order-1-drink-1"})
        assert (await runtime.queue_snapshot()).totalDrinks == 1
        stored = await runtime.store.get_order("order-1")
        assert stored is not None
        assert stored.drinks[0].timeComplete is None
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_intake_domain_failure_has_no_persistence_effect(
    tmp_path, queue_settings, monkeypatch
):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'intake-domain-failure.db'}",
        queue_settings,
    )

    def fail(_queue, _order):
        raise RuntimeError("domain mutation failed")

    monkeypatch.setattr(Queue, "add_order", fail)
    try:
        with pytest.raises(RuntimeError):
            await runtime.intake(make_order("order-1"))
        assert await runtime.store.get_order("order-1") is None
        assert (await runtime.queue_snapshot()).totalDrinks == 0
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_completion_domain_failure_has_no_persistence_effect(
    tmp_path, queue_settings, monkeypatch
):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'completion-domain-failure.db'}",
        queue_settings,
    )
    await runtime.intake(make_order("order-1"))

    def fail(_queue, _identifiers, _completed_at):
        raise RuntimeError("domain mutation failed")

    monkeypatch.setattr(Queue, "complete_drinks", fail)
    try:
        with pytest.raises(RuntimeError):
            await runtime.complete({"order-1-drink-1"})
        stored = await runtime.store.get_order("order-1")
        assert stored is not None
        assert stored.drinks[0].timeComplete is None
        assert (await runtime.queue_snapshot()).totalDrinks == 1
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_successful_mutations_are_persisted_before_notifications(
    tmp_path, queue_settings, monkeypatch
):
    runtime = await QueueRuntime.create(
        f"sqlite+aiosqlite:///{tmp_path / 'notification-order.db'}",
        queue_settings,
    )
    notifications: list[int] = []

    async def record(revision: int):
        stored = await runtime.store.get_order("order-1")
        assert stored is not None
        if revision == 1:
            assert stored.drinks[0].timeComplete is None
        else:
            assert stored.drinks[0].timeComplete is not None
        notifications.append(revision)

    monkeypatch.setattr(runtime.events, "broadcast_change", record)
    try:
        await runtime.intake(make_order("order-1"))
        await runtime.complete({"order-1-drink-1"})
        assert notifications == [1, 2]
        assert (await runtime.queue_snapshot()).totalDrinks == 0
    finally:
        await runtime.close()
