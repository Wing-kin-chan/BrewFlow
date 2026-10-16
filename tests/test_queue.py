from datetime import time

import pytest

from brewflow.domain.queue import Batch, Queue
from tests.conftest import make_order


def test_batches_only_matching_milk_and_texture_and_sorts_temperature(queue_settings):
    order = make_order(
        "order-1",
        [
            {"identifier": "hot", "drink": "Latte", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Extra Hot", "texture": "Wet", "options": []},
            {"identifier": "warm", "drink": "Flat White", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Warm", "texture": "Wet", "options": []},
            {"identifier": "normal", "drink": "Latte", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []},
            {"identifier": "dry", "drink": "Cappuccino", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Normal", "texture": "Dry", "options": []},
        ],
    )
    queue = Queue(queue_settings)

    queue.add_order(order)

    batch = next(item for item in queue.items if isinstance(item, Batch))
    assert [drink.identifier for drink in batch.drinks] == ["warm", "normal", "hot"]
    assert all(drink.texture == "Wet" for drink in batch.drinks)
    assert queue.total_orders == 1
    assert queue.total_drinks == 4


@pytest.mark.parametrize("texture", ("Extra Wet", "Wet", "Dry", "Extra Dry"))
def test_all_product_textures_can_batch(texture, queue_settings):
    queue = Queue(queue_settings)
    queue.add_order(
        make_order(
            f"order-{texture}",
            [
                {"identifier": f"{texture}-warm", "drink": "Latte", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Warm", "texture": texture, "options": []},
                {"identifier": f"{texture}-hot", "drink": "Latte", "milk": "Whole", "milk_volume": 1, "shots": 2, "temperature": "Extra Hot", "texture": texture, "options": []},
            ],
        )
    )

    assert len(queue.items) == 1
    assert isinstance(queue.items[0], Batch)
    assert queue.items[0].texture == texture
    assert [drink.temperature for drink in queue.items[0].drinks] == ["Warm", "Extra Hot"]


def test_cross_order_batch_respects_capacity(queue_settings):
    queue = Queue(queue_settings)
    queue.add_order(make_order("order-1"))
    queue.add_order(
        make_order(
            "order-2",
            [{"identifier": "order-2-drink", "drink": "Latte", "milk": "Whole", "milk_volume": 3, "shots": 2, "temperature": "Warm", "texture": "Wet", "options": []}],
        )
    )

    assert len(queue.items) == 1
    assert isinstance(queue.items[0], Batch)
    assert queue.items[0].volume == 5
    assert {drink.orderID for drink in queue.items[0].drinks} == {"order-1", "order-2"}


def test_over_capacity_drink_stays_in_parent_order(queue_settings):
    queue = Queue(queue_settings)
    queue.add_order(
        make_order(
            "order-1",
            [
                {"identifier": "one", "drink": "Latte", "milk": "Whole", "milk_volume": 3, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []},
                {"identifier": "two", "drink": "Latte", "milk": "Whole", "milk_volume": 3, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []},
            ],
        )
    )

    assert all(not isinstance(item, Batch) for item in queue.items)
    assert queue.total_drinks == 2


def test_history_has_one_parent_and_completion_is_repeat_safe(queue_settings):
    queue = Queue(queue_settings)
    order = make_order("order-1")
    queue.add_order(order)

    completed = queue.complete_drinks({"order-1-drink-1"}, time(9, 5))
    repeated = queue.complete_drinks({"order-1-drink-1"}, time(9, 6))

    assert completed == {"order-1-drink-1"}
    assert repeated == set()
    assert len(queue.history) == 1
    assert queue.history[0].timeComplete == time(9, 5)
    history = queue.history_snapshot(2)
    assert len(history.orders) == 1
    assert len(history.orders[0].drinks) == 1
    assert queue.total_drinks == 0


def test_partial_multiple_and_full_completion_stays_grouped_by_parent(queue_settings):
    queue = Queue(queue_settings)
    queue.add_order(
        make_order(
            "order-1",
            [
                {"identifier": "one", "drink": "Latte", "milk": "Whole", "milk_volume": 2, "shots": 2, "temperature": "Warm", "texture": "Wet", "options": []},
                {"identifier": "two", "drink": "Latte", "milk": "Whole", "milk_volume": 2, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []},
                {"identifier": "three", "drink": "Espresso", "milk": "No Milk", "milk_volume": 0, "shots": 2, "temperature": "Normal", "texture": None, "options": []},
            ],
        )
    )

    assert queue.complete_drinks({"one", "three"}, time(9, 5)) == {"one", "three"}
    partial = queue.history_snapshot(1)
    assert partial.totalOrders == 0
    assert {drink.identifier for drink in partial.orders[0].drinks} == {"one", "three"}

    assert queue.complete_drinks({"two"}, time(9, 6)) == {"two"}
    complete = queue.history_snapshot(2)
    assert complete.totalOrders == 1
    assert complete.orders[0].timeComplete == time(9, 6)


def test_search_depth_protects_front_of_queue(queue_settings):
    protected_settings = type(queue_settings)(
        drinks=queue_settings.drinks,
        milks=queue_settings.milks,
        textures=queue_settings.textures,
        search_depth=1,
        max_batch_volume=queue_settings.max_batch_volume,
    )
    queue = Queue(protected_settings)
    queue.add_order(make_order("order-1"))
    queue.add_order(make_order("order-2"))

    assert len(queue.items) == 2
    assert all(not isinstance(item, Batch) for item in queue.items)
