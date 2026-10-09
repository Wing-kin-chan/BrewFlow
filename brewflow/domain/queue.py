from __future__ import annotations

from copy import deepcopy
from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

from brewflow.domain.models import Drink, Order
from brewflow.settings import QueueSettings


TEMPERATURE_ORDER = {"Warm": 0, "Normal": 1, "Extra Hot": 2}


class Batch(BaseModel):
    drinks: list[Drink] = Field(default_factory=list)
    milk: str
    texture: str
    volume: float = 0

    def add_drink(self, drink: Drink) -> None:
        self.drinks.append(drink)
        self.drinks.sort(key=lambda item: TEMPERATURE_ORDER[item.temperature])
        self.volume = sum(item.milk_volume for item in self.drinks)

    def can_add(self, drink: Drink, capacity: float) -> bool:
        return (
            self.milk == drink.milk
            and self.texture == drink.texture
            and self.volume + drink.milk_volume <= capacity
        )


class OrderQueueItem(BaseModel):
    kind: Literal["order"] = "order"
    orderID: str
    customer: str
    timeReceived: time | None
    drinks: list[Drink]


class BatchQueueItem(BaseModel):
    kind: Literal["batch"] = "batch"
    milk: str
    texture: str
    volume: float
    drinks: list[Drink]


class QueueSnapshot(BaseModel):
    revision: int
    items: list[OrderQueueItem | BatchQueueItem]
    totalOrders: int
    totalDrinks: int


class HistorySnapshot(BaseModel):
    revision: int
    orders: list[Order]
    totalOrders: int
    totalDrinks: int


class Queue:
    def __init__(self, settings: QueueSettings):
        self.settings = settings
        self.items: list[Order | Batch] = []
        self.history: list[Order] = []
        self.history_by_id: dict[str, Order] = {}

    @property
    def pending_drink_ids(self) -> set[str]:
        return {drink.identifier for item in self.items for drink in item.drinks}

    @property
    def total_drinks(self) -> int:
        return len(self.pending_drink_ids)

    @property
    def total_orders(self) -> int:
        return len({drink.orderID for item in self.items for drink in item.drinks})

    def _add_history(self, order: Order) -> None:
        history_order = deepcopy(order)
        self.history.insert(0, history_order)
        self.history_by_id[order.orderID] = history_order

    def load_order(self, order: Order) -> None:
        self._add_history(order)
        if order.timeComplete is not None:
            return
        pending = deepcopy(order)
        pending.drinks = [drink for drink in pending.drinks if drink.timeComplete is None]
        if pending.drinks:
            self.add_order(pending, add_history=False)

    def add_order(self, order: Order, *, add_history: bool = True) -> None:
        queue_order = deepcopy(order)
        if add_history:
            self._add_history(order)
        self.items.append(queue_order)
        self._batch_within_order(queue_order)
        self._batch_with_existing_items(queue_order)
        if not queue_order.drinks and queue_order in self.items:
            self.items.remove(queue_order)

    def _batch_within_order(self, order: Order) -> None:
        grouped_ids: set[str] = set()
        insert_at = self.items.index(order)
        for group in order.group_drinks():
            chunk: list[Drink] = []
            volume = 0.0
            chunks: list[list[Drink]] = []
            for drink in group:
                if drink.milk_volume > self.settings.max_batch_volume:
                    continue
                if chunk and volume + drink.milk_volume > self.settings.max_batch_volume:
                    chunks.append(chunk)
                    chunk = []
                    volume = 0.0
                chunk.append(drink)
                volume += drink.milk_volume
            if chunk:
                chunks.append(chunk)

            for batch_drinks in chunks:
                if len(batch_drinks) < 2:
                    continue
                batch = Batch(
                    milk=batch_drinks[0].milk,
                    texture=batch_drinks[0].texture,
                )
                for drink in batch_drinks:
                    batch.add_drink(drink)
                    grouped_ids.add(drink.identifier)
                self.items.insert(insert_at, batch)
                insert_at += 1

        if grouped_ids:
            order.drinks = [
                drink for drink in order.drinks if drink.identifier not in grouped_ids
            ]

    def _batch_with_existing_items(self, order: Order) -> None:
        for drink in list(order.drinks):
            if drink.milk == "No Milk" or drink.milk_volume > self.settings.max_batch_volume:
                continue
            order_index = self.items.index(order)
            candidate_indexes = range(
                order_index - 1,
                self.settings.search_depth - 1,
                -1,
            )
            for index in candidate_indexes:
                candidate = self.items[index]
                if isinstance(candidate, Batch):
                    if candidate.can_add(drink, self.settings.max_batch_volume):
                        candidate.add_drink(drink)
                        order.drinks.remove(drink)
                        break
                    continue

                compatible = [
                    existing
                    for existing in candidate.drinks
                    if existing.milk == drink.milk
                    and existing.texture == drink.texture
                    and existing.milk != "No Milk"
                ]
                selected: list[Drink] = []
                volume = drink.milk_volume
                for existing in compatible:
                    if volume + existing.milk_volume <= self.settings.max_batch_volume:
                        selected.append(existing)
                        volume += existing.milk_volume
                if not selected:
                    continue

                batch = Batch(milk=drink.milk, texture=drink.texture)
                for existing in selected:
                    batch.add_drink(existing)
                    candidate.drinks.remove(existing)
                batch.add_drink(drink)
                order.drinks.remove(drink)
                if not candidate.drinks:
                    self.items.pop(index)
                self.items.insert(index, batch)
                break

    def complete_drinks(self, identifiers: set[str], completed_at: time) -> set[str]:
        completed = identifiers & self.pending_drink_ids
        if not completed:
            return set()

        for item in self.items:
            item.drinks = [
                drink for drink in item.drinks if drink.identifier not in completed
            ]
            if isinstance(item, Batch):
                item.volume = sum(drink.milk_volume for drink in item.drinks)
        self.items = [item for item in self.items if item.drinks]

        affected_orders: set[str] = set()
        for order in self.history:
            for drink in order.drinks:
                if drink.identifier in completed:
                    drink.timeComplete = completed_at
                    affected_orders.add(order.orderID)
            if order.orderID in affected_orders and all(
                drink.timeComplete is not None for drink in order.drinks
            ):
                order.timeComplete = completed_at
        return completed

    def queue_snapshot(self, revision: int) -> QueueSnapshot:
        items: list[OrderQueueItem | BatchQueueItem] = []
        for item in self.items:
            if isinstance(item, Batch):
                items.append(
                    BatchQueueItem(
                        milk=item.milk,
                        texture=item.texture,
                        volume=item.volume,
                        drinks=deepcopy(item.drinks),
                    )
                )
            else:
                items.append(
                    OrderQueueItem(
                        orderID=item.orderID,
                        customer=item.customer,
                        timeReceived=item.timeReceived,
                        drinks=deepcopy(item.drinks),
                    )
                )
        return QueueSnapshot(
            revision=revision,
            items=items,
            totalOrders=self.total_orders,
            totalDrinks=self.total_drinks,
        )

    def history_snapshot(self, revision: int) -> HistorySnapshot:
        orders: list[Order] = []
        for order in self.history:
            completed_drinks = [
                deepcopy(drink) for drink in order.drinks if drink.timeComplete is not None
            ]
            if completed_drinks:
                completed_order = deepcopy(order)
                completed_order.drinks = completed_drinks
                orders.append(completed_order)
        return HistorySnapshot(
            revision=revision,
            orders=orders,
            totalOrders=sum(order.timeComplete is not None for order in self.history),
            totalDrinks=sum(len(order.drinks) for order in orders),
        )
