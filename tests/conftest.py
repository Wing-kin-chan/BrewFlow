from datetime import datetime

import pytest

from brewflow.domain.models import Order
from brewflow.settings import QueueSettings


@pytest.fixture
def queue_settings() -> QueueSettings:
    return QueueSettings(
        drinks=(
            "Latte",
            "Cappuccino",
            "Flat White",
            "Espresso",
        ),
        milks=("Whole", "Semi-skimmed", "Oat", "Soy"),
        textures=("Extra Wet", "Wet", "Dry", "Extra Dry"),
        search_depth=0,
        max_batch_volume=5,
    )


def make_order(
    order_id: str,
    drinks: list[dict] | None = None,
    *,
    customer: str = "Ada",
) -> Order:
    drink_values = drinks or [
        {
            "identifier": f"{order_id}-drink-1",
            "drink": "Latte",
            "milk": "Whole",
            "milk_volume": 2,
            "shots": 2,
            "temperature": "Normal",
            "texture": "Wet",
            "options": [],
        }
    ]
    return Order(
        orderID=order_id,
        customer=customer,
        dateReceived=datetime(2020, 1, 1).date(),
        timeReceived=datetime(2020, 1, 1, 1).time(),
        drinks=drink_values,
    )
