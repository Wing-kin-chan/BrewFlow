from datetime import date, datetime, time
import sqlite3

import pytest
from sqlalchemy import inspect

from brewflow.persistence.db import Base, Database
from brewflow.persistence.orders import OrderStore, decode_options
from tests.conftest import make_order


def test_original_schema_metadata_is_unchanged_and_stage_2_additions_are_exact():
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
    assert not orders.indexes
    assert not drinks.indexes

    pos_orders = Base.metadata.tables["pos_orders"]
    pos_items = Base.metadata.tables["pos_order_items"]
    attempts = Base.metadata.tables["payment_attempts"]
    cafes = Base.metadata.tables["cafe_accounts"]
    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in pos_orders.columns] == [
        ("orderID", "String", False, True),
        ("customer", "String", False, False),
        ("currency", "String", False, False),
        ("totalMinor", "Integer", False, False),
        ("status", "String", False, False),
        ("createdAt", "DateTime", False, False),
        ("paidAt", "DateTime", True, False),
        ("queuedAt", "DateTime", True, False),
    ]
    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in pos_items.columns] == [
        ("identifier", "String", False, True),
        ("orderID", "String", False, False),
        ("lineNumber", "Integer", False, False),
        ("catalogItemID", "String", False, False),
        ("itemName", "String", False, False),
        ("unitAmountMinor", "Integer", False, False),
        ("drinkSnapshot", "Text", False, False),
    ]
    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in attempts.columns] == [
        ("attemptID", "String", False, True),
        ("orderID", "String", False, False),
        ("idempotencyKey", "String", False, False),
        ("stripeSessionID", "String", True, False),
        ("stripePaymentIntentID", "String", True, False),
        ("checkoutURL", "Text", True, False),
        ("status", "String", False, False),
        ("createdAt", "DateTime", False, False),
        ("updatedAt", "DateTime", False, False),
        ("expiresAt", "DateTime", True, False),
        ("paidAt", "DateTime", True, False),
        ("isDemo", "Boolean", False, False),
    ]
    assert [(column.name, type(column.type).__name__, column.nullable, column.primary_key) for column in cafes.columns] == [
        ("cafeID", "String", False, True),
        ("demoModeEnabled", "Boolean", False, False),
    ]
    assert {str(foreign_key.column) for foreign_key in pos_items.c.orderID.foreign_keys} == {"pos_orders.orderID"}
    assert {str(foreign_key.column) for foreign_key in attempts.c.orderID.foreign_keys} == {"pos_orders.orderID"}
    assert {constraint.name for constraint in pos_orders.constraints if constraint.name} == {
        "ck_pos_orders_currency",
        "ck_pos_orders_status",
        "ck_pos_orders_total_minor",
    }
    assert {constraint.name for constraint in pos_items.constraints if constraint.name} == {
        "ck_pos_order_items_line_number",
        "ck_pos_order_items_unit_amount_minor",
        "uq_pos_order_items_line",
    }
    assert {constraint.name for constraint in attempts.constraints if constraint.name} == {
        "ck_payment_attempts_status",
        "uq_payment_attempts_idempotency_key",
        "uq_payment_attempts_stripe_session_id",
        "uq_payment_attempts_payment_intent_id",
    }


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
async def test_database_contains_only_approved_tables(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'schema.db'}")
    await database.initialize()
    try:
        async with database.engine.connect() as connection:
            table_names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            foreign_keys = (await connection.exec_driver_sql("PRAGMA foreign_keys")).scalar_one()
        assert table_names == [
            "cafe_accounts",
            "drinks",
            "orders",
            "payment_attempts",
            "pos_order_items",
            "pos_orders",
        ]
        assert foreign_keys == 1
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_sqlite_migration_adds_demo_provenance_without_losing_stripe_data(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE pos_orders (
          "orderID" VARCHAR PRIMARY KEY, customer VARCHAR NOT NULL,
          currency VARCHAR NOT NULL, "totalMinor" INTEGER NOT NULL,
          status VARCHAR NOT NULL, "createdAt" DATETIME NOT NULL,
          "paidAt" DATETIME, "queuedAt" DATETIME
        );
        CREATE TABLE payment_attempts (
          "attemptID" VARCHAR PRIMARY KEY, "orderID" VARCHAR NOT NULL,
          "idempotencyKey" VARCHAR NOT NULL, "stripeSessionID" VARCHAR,
          "stripePaymentIntentID" VARCHAR, "checkoutURL" TEXT,
          status VARCHAR NOT NULL, "createdAt" DATETIME NOT NULL,
          "updatedAt" DATETIME NOT NULL, "expiresAt" DATETIME,
          "paidAt" DATETIME
        );
        INSERT INTO pos_orders VALUES (
          'order-1', 'Ada', 'gbp', 400, 'pending_payment',
          '2026-10-09 09:00:00', NULL, NULL
        );
        INSERT INTO payment_attempts VALUES (
          'attempt-1', 'order-1', 'checkout-session:attempt-1',
          'cs_test_existing', NULL, 'https://checkout.stripe.com/test/existing',
          'open', '2026-10-09 09:00:00', '2026-10-09 09:00:00', NULL, NULL
        );
        """
    )
    connection.commit()
    connection.close()

    database = Database(f"sqlite+aiosqlite:///{path}")
    await database.initialize()
    await database.initialize()
    try:
        async with database.engine.connect() as async_connection:
            columns = await async_connection.run_sync(
                lambda sync: {
                    column["name"]
                    for column in inspect(sync).get_columns("payment_attempts")
                }
            )
            row = (
                await async_connection.exec_driver_sql(
                    'SELECT "stripeSessionID", "checkoutURL", "isDemo" '
                    'FROM payment_attempts WHERE "attemptID" = ?',
                    ("attempt-1",),
                )
            ).one()
            cafe = (
                await async_connection.exec_driver_sql(
                    'SELECT "cafeID", "demoModeEnabled" FROM cafe_accounts'
                )
            ).one()
        assert "isDemo" in columns
        assert row == (
            "cs_test_existing",
            "https://checkout.stripe.com/test/existing",
            0,
        )
        assert cafe == ("local", 0)
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
