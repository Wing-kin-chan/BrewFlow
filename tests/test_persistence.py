from datetime import date, datetime, time

import pytest
from sqlalchemy import inspect

from brewflow.persistence.db import Base, Database
from brewflow.persistence.orders import OrderStore, decode_options
from tests.conftest import make_order


def test_schema_metadata_is_unchanged():
    orders = Base.metadata.tables["orders"]
    drinks = Base.metadata.tables["drinks"]

    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in orders.columns] == [
        ("orderID", "String", False, True),
        ("customer", "String", False, False),
        ("dateReceived", "Date", False, False),
        ("timeReceived", "Time", False, False),
        ("timeComplete", "Time", True, False),
    ]
    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in drinks.columns] == [
        ("identifier", "String", False, True),
        ("orderID", "String", True, False),
        ("drink", "String", False, False),
        ("milk", "String", True, False),
        ("milk_volume", "Float", True, False),
        ("shots", "Integer", False, False),
        ("temperature", "String", True, False),
        ("texture", "String", True, False),
        ("options", "String", True, False),
        ("customer", "String", True, False),
        ("timeReceived", "Time", True, False),
        ("timeComplete", "Time", True, False),
    ]
    assert {str(foreign_key.column) for foreign_key in drinks.c.orderID.foreign_keys} == {"orders.orderID"}


def test_legacy_comma_separated_options_remain_readable():
    assert decode_options("Decaf,Warm") == ["Decaf", "Warm"]
    assert decode_options("") == []


@pytest.mark.asyncio
async def test_order_round_trip_and_atomic_completion(tmp_path):
    uri = f"sqlite+aiosqlite:///{tmp_path / 'orders.db'}"
    store = await OrderStore.create(uri)
    order = make_order(
        "order-1",
        [
            {"identifier": "one", "drink": "Latte", "milk": "Whole", "milk_volume": 2, "shots": 2, "temperature": "Normal", "texture": "Wet", "options": []},
            {"identifier": "two", "drink": "Latte", "milk": "Whole", "milk_volume": 2, "shots": 2, "temperature": "Warm", "texture": "Wet", "options": []},
        ],
    )
    try:
        await store.add_order(order)
        recalled = await store.get_order(order.orderID)
        assert recalled == order

        await store.complete_drinks({"one"}, time(9, 5))
        partial = await store.get_order(order.orderID)
        assert partial is not None
        assert partial.timeComplete is None

        await store.complete_drinks({"two"}, time(9, 6))
        complete = await store.get_order(order.orderID)
        assert complete is not None
        assert complete.timeComplete == time(9, 6)
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_database_contains_only_original_tables(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'schema.db'}")
    await database.initialize()
    try:
        async with database.engine.connect() as connection:
            table_names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
        assert table_names == ["drinks", "orders"]
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_options_json_round_trip_preserves_commas_empty_strings_and_list(tmp_path):
    store = await OrderStore.create(f"sqlite+aiosqlite:///{tmp_path / 'options.db'}")
    order = make_order("options-order")
    order.drinks[0].options = ["vanilla,caramel", "", "plain"]
    try:
        await store.add_order(order)
        recalled = await store.get_order(order.orderID)
        assert recalled is not None
        assert recalled.drinks[0].options == ["vanilla,caramel", "", "plain"]
    finally:
        await store.close()
