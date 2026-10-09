from asyncio import Lock
from copy import deepcopy
from collections.abc import Callable
from datetime import datetime

from brewflow.domain.models import Order
from brewflow.domain.queue import HistorySnapshot, Queue, QueueSnapshot
from brewflow.events import QueueEvents
from brewflow.persistence.orders import OrderStore
from brewflow.settings import QueueSettings


class IntakeConflictError(Exception):
    pass


class InvalidOrderValueError(Exception):
    pass


class QueueRuntime:
    def __init__(
        self,
        store: OrderStore,
        settings: QueueSettings,
        *,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.store = store
        self.settings = settings
        self.queue = Queue(settings)
        self.events = QueueEvents()
        self.lock = Lock()
        self.revision = 0
        self._now = now

    @classmethod
    async def create(
        cls,
        database_uri: str,
        settings: QueueSettings,
        *,
        now: Callable[[], datetime] = datetime.now,
    ) -> "QueueRuntime":
        store = await OrderStore.create(database_uri)
        runtime = cls(store, settings, now=now)
        await runtime.reload()
        return runtime

    async def close(self) -> None:
        await self.store.close()

    async def reload(self) -> None:
        queue = Queue(self.settings)
        for order in await self.store.service_orders(self._now().date()):
            queue.load_order(order)
        self.queue = queue

    def _validate_order(self, order: Order) -> None:
        unknown_drinks = sorted(
            {drink.drink for drink in order.drinks if drink.drink not in self.settings.drinks}
        )
        if unknown_drinks:
            raise InvalidOrderValueError(
                f"Unknown drink value: {', '.join(unknown_drinks)}"
            )

        valid_milks = set(self.settings.milks) | {"No Milk"}
        unknown_milks = sorted(
            {drink.milk for drink in order.drinks if drink.milk not in valid_milks}
        )
        if unknown_milks:
            raise InvalidOrderValueError(
                f"Unknown milk value: {', '.join(unknown_milks)}"
            )

        unknown_textures = sorted(
            {
                drink.texture
                for drink in order.drinks
                if drink.texture is not None and drink.texture not in self.settings.textures
            }
        )
        if unknown_textures:
            raise InvalidOrderValueError(
                f"Unknown texture value: {', '.join(unknown_textures)}"
            )

    async def intake(self, submitted: Order) -> tuple[str, QueueSnapshot]:
        self._validate_order(submitted)
        async with self.lock:
            existing = await self.store.get_order(submitted.orderID)
            if existing is not None:
                if existing.stable_payload() != submitted.stable_payload():
                    raise IntakeConflictError("Order identifier already has different content")
                return "duplicate", self.queue.queue_snapshot(self.revision)

            drink_ids = {drink.identifier for drink in submitted.drinks}
            if await self.store.drink_identifiers_exist(drink_ids):
                raise IntakeConflictError("A drink identifier is already in use")

            order = deepcopy(submitted)
            order.stamp_received(self._now())
            candidate = deepcopy(self.queue)
            candidate.add_order(order)
            revision = self.revision + 1
            snapshot = candidate.queue_snapshot(revision)
            await self.store.add_order(order)
            self.queue = candidate
            self.revision = revision
        await self.events.broadcast_change(revision)
        return "accepted", snapshot

    async def complete(self, identifiers: set[str]) -> QueueSnapshot:
        revision: int | None = None
        async with self.lock:
            pending = identifiers & self.queue.pending_drink_ids
            if pending:
                completed_at = self._now().time()
                candidate = deepcopy(self.queue)
                candidate.complete_drinks(pending, completed_at)
                revision = self.revision + 1
                snapshot = candidate.queue_snapshot(revision)
                await self.store.complete_drinks(pending, completed_at)
                self.queue = candidate
                self.revision = revision
            else:
                snapshot = self.queue.queue_snapshot(self.revision)
        if revision is not None:
            await self.events.broadcast_change(revision)
        return snapshot

    async def queue_snapshot(self) -> QueueSnapshot:
        async with self.lock:
            return self.queue.queue_snapshot(self.revision)

    async def history_snapshot(self) -> HistorySnapshot:
        async with self.lock:
            return self.queue.history_snapshot(self.revision)
