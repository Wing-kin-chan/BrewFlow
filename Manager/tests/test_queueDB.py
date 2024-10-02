import pytest
from typing import List
from datetime import datetime, timedelta
from sqlalchemy import select, asc
from sqlalchemy.orm import joinedload

from Manager.app.scripts.services.CRUD import Connection
from Manager.app.scripts.services import PydanticORM
from Manager.app.models.db import Orders, Drinks
from Manager.app.models import Order, Drink

TEST_DATABASE_URI = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def connection() -> Connection:
    conn = await Connection.new(TEST_DATABASE_URI)

    try:
        return conn
    finally:
        await conn.clearQueue()
        await conn.session.close()


@pytest.fixture(scope='session')
def adam_order():
    date, time = datetime.now().date(), datetime.now().time()
    adam_drink = {
        'orderID': 12345,
        'drink': 'Latte',
        'milk': 'Whole',
        'milk_volume': 2,
        'shots': 2,
        'temperature': None,
        'texture': 'Wet',
        'options': [],
        'customer': 'Adam',
        'timeComplete': None
    }
    return Order.model_validate({
        'orderID': 12345,
        'dateReceived': date,
        'timeReceived': time,
        'customer': 'Adam',
        'drinks': [adam_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def jeff_order():
    today = datetime.now().date()
    yesterday = today - timedelta(days = 1)
    time =  datetime.now().time()
    jeff_drink = {
        'orderID': 56789,
        'drink': 'Latte',
        'milk': 'Whole',
        'milk_volume': 2,
        'shots': 2,
        'temperature': None,
        'texture': 'Wet',
        'options': [],
        'customer': 'Jeff',
        'timeComplete': None
    }
    return Order.model_validate({
        'orderID': 56789,
        'dateReceived': yesterday,
        'timeReceived': time,
        'customer': 'Jeff',
        'drinks': [jeff_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def hannah_order():
    date, time = datetime.now().date(), datetime.now().time()
    hannah_drinks = [
        {
            'orderID': 23456,
            'drink': 'Cappuccino',
            'milk': 'Oat',
            'milk_volume': 2,
            'shots': 1,
            'temperature': None,
            'texture': 'Dry',
            'options': [],
            'customer': 'Hannah',
            'timeComplete': None
        },
        {
            'orderID': 23456,
            'drink': 'Cappuccino',
            'milk': 'Oat',
            'milk_volume': 2,
            'shots': 1,
            'temperature': None,
            'texture': 'Dry',
            'options': [],
            'customer': 'Hannah',
            'timeComplete': None
        },
        {
            'orderID': 23456,
            'drink': 'Cappuccino',
            'milk': 'Soy',
            'milk_volume': 2,
            'shots': 2,
            'temperature': None,
            'texture': 'Dry',
            'options': [],
            'customer': 'Hannah',
            'timeComplete': None
        }
    ]
    return Order.model_validate({
        'orderID': 23456,
        'customer': 'Hannah',
        'dateReceived': date,
        'timeReceived': time,
        'drinks': hannah_drinks,
        'timeComplete': None
    })


class TestConnection:
    @pytest.mark.asyncio
    async def test_connection_type(self, connection):
        try:
            conn = await connection
            print(f"Connection type: {type(conn)}")
            assert isinstance(conn, Connection)
        finally:
            await conn.close()


class TestCreateOperations:
    @pytest.mark.asyncio
    async def test_addOrder(self, connection, adam_order):
        try:
            conn: Connection = await connection
            await conn.addOrder(adam_order)
            
            result = await conn.session.execute(
                select(Orders)
                .where(Orders.orderID == adam_order.orderID)
                .options(joinedload(Orders.drinks))
            )
            recall: Orders = result.unique().scalar_one_or_none()
            order = PydanticORM.readOrdersORM(recall)

            assert order == adam_order

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_addOrder_multiple_drinks(self, connection, hannah_order):
        try:
            conn: Connection = await connection
            await conn.addOrder(hannah_order)

            result = await conn.session.execute(
                select(Orders)
                .where(Orders.orderID == hannah_order.orderID)
                .options(joinedload(Orders.drinks))
            )

            recall: Orders = result.unique().scalar_one_or_none()
            order = PydanticORM.readOrdersORM(recall)

            assert order == hannah_order
            
        finally:
            await conn.close()

class TestUpdateOperations:
    @pytest.mark.asyncio
    async def test_completeOrder(self, connection, adam_order):
        current_time = datetime.now().time()
        try:
            conn: Connection = await connection
            await conn.addOrder(adam_order)
            await conn.completeOrder(orderID = adam_order.orderID, time = current_time)

            result = await conn.session.execute(
                select(Orders)
                .where(Orders.orderID == adam_order.orderID)
            )
            order: Orders = result.scalar_one_or_none()

            assert order.timeComplete == current_time
        
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_completeDrink(self, connection, hannah_order):
        current_time = datetime.now().time()
        drinkID = hannah_order.drinks[0].identifier
        try:
            conn: Connection = await connection
            await conn.addOrder(hannah_order)
            await conn.completeDrink(identifier = drinkID, time = current_time)

            result = await conn.session.execute(
                select(Drinks)
                .where(Drinks.identifier == drinkID)
            )
            drink: Drinks = result.scalar_one_or_none()

            assert drink.identifier == drinkID
            assert drink.timeComplete == current_time
        
        finally:
            await conn.close()

class TestReadOperations:
    @pytest.mark.asyncio
    async def test_getQueue(self, connection, adam_order, hannah_order, jeff_order):
        queue: List[Order] = [adam_order, hannah_order]
        try:
            conn: Connection = await connection
            await conn.addOrder(jeff_order)
            await conn.addOrder(adam_order)
            await conn.addOrder(hannah_order)

            result = await conn.getQueue()

            for recall, original in zip(result, queue):
                assert recall.orderID == original.orderID
                assert recall.customer == original.customer
                assert recall.timeReceived == original.timeReceived
                assert recall.timeComplete == original.timeComplete
                assert recall.dateReceived == original.dateReceived
                assert set(recall.drinks) == set(original.drinks)
        
        finally:
            await conn.close()

class TestDeleteOperations:
    @pytest.mark.asyncio
    async def test_clearQueue(self, connection, adam_order, hannah_order):
        try:
            conn: Connection = await connection
            await conn.addOrder(adam_order)
            await conn.addOrder(hannah_order)
            await conn.clearQueue()

            orders_result = await conn.session.scalar(select(Orders).limit(1))
            drinks_result = await conn.session.scalar(select(Drinks).limit(1))
            
            assert orders_result is None and drinks_result is None
        
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_clearOldRecords(self, connection, adam_order, hannah_order, jeff_order):
        queue: List[Order] = [adam_order, hannah_order]
        try:
            conn: Connection = await connection
            await conn.addOrder(jeff_order)
            await conn.addOrder(adam_order)
            await conn.addOrder(hannah_order)
            
            await conn.clearOldRecords()

            result = await conn.session.execute(
                select(Orders).
                options(joinedload(Orders.drinks)).
                order_by(asc(Orders.timeReceived))
            )

            result: List[Orders] = result.unique().scalars().all()

            for obj, original in zip(result, queue):
                order = PydanticORM.readOrdersORM(obj)
                assert order.orderID == original.orderID
                assert order.customer == original.customer
                assert order.timeReceived == original.timeReceived
                assert order.timeComplete == original.timeComplete
                assert order.dateReceived == original.dateReceived
                assert set(order.drinks) == set(original.drinks)
            
        finally:
            await conn.close()
