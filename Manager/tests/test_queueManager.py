import pytest
from datetime import datetime
import logging, sys, uuid
from tqdm import trange

from Manager.app.scripts.queueManager import Queue, Batch, fetchOrder
from Manager.app.models import Order, Drink

@pytest.fixture(scope='module')
def orders():
    logging.info("Generating random orders")
    return [fetchOrder.fetchOrder() for _ in trange(0, 50, file=sys.stdout)]

@pytest.fixture(scope='session')
def date_time():
    return datetime.now().date(), datetime.now().time()

@pytest.fixture(scope='session')
def queue() -> Queue:
    return Queue()

@pytest.fixture(scope='session')
def jeff_order(date_time):
    date, time = date_time
    orderID = uuid.uuid4().hex
    jeff_drink = {
        'orderID': orderID,
        'drink': 'double_espresso',
        'milk': 'No Milk',
        'milk_volume': 0,
        'shots': 2,
        'temperature': None,
        'texture': None,
        'options': [],
        'customer': 'Jeff',
        'timeComplete': None
    }
    return Order.model_validate({
        'orderID': orderID,
        'dateReceived': date,
        'timeReceived': time,
        'customer': 'Jeff',
        'drinks': [jeff_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def kayleigh_order(date_time):
    date, time = date_time
    orderID = uuid.uuid4().hex
    kayleigh_drink = {
        'orderID': orderID,
        'drink': 'Flat White',
        'milk': 'Whole',
        'milk_volume': 1,
        'shots': 2,
        'temperature': None,
        'texture': 'Wet',
        'options': [],
        'customer': 'Kayleigh',
        'timeComplete': None
    }
    return Order.model_validate({
        'orderID': orderID,
        'dateReceived': date,
        'timeReceived': time,
        'customer': 'Kayleigh',
        'drinks': [kayleigh_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def adam_order(date_time):
    date, time = date_time
    orderID = uuid.uuid4().hex
    adam_drink = {
        'orderID': orderID,
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
        'orderID': orderID,
        'dateReceived': date,
        'timeReceived': time,
        'customer': 'Adam',
        'drinks': [adam_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def hannah_order(date_time):
    date, time = date_time
    orderID = uuid.uuid4().hex
    hannah_drinks = [
        {
            'orderID': orderID,
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
            'orderID': orderID,
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
            'orderID': orderID,
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
        'orderID': orderID,
        'customer': 'Hannah',
        'dateReceived': date,
        'timeReceived': time,
        'drinks': hannah_drinks,
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def oat_cappuccinos(hannah_order) -> Drink:
    return [drink for drink in hannah_order.drinks if drink.milk == 'Oat']

@pytest.fixture(scope='session')
def soy_cappuccino(hannah_order) -> Drink:
    return next(drink for drink in hannah_order.drinks if drink.milk == 'Soy')


class TestQueueInitialization:
    def test_queue_initialization(self, queue):
        assert hasattr(queue, 'orders')
        assert hasattr(queue, 'orderHistory')
        assert hasattr(queue, 'lookupTable')
        assert hasattr(queue, 'totalDrinks')
        assert hasattr(queue, 'totalOrders')
        assert isinstance(queue.orders, list)
        assert isinstance(queue.orderHistory, list)
        assert isinstance(queue.orderHistoryIndex, dict)
        assert isinstance(queue.totalOrders, int)
        assert isinstance(queue.totalDrinks, int)
        assert isinstance(queue.lookupTable, dict)


class TestQueueOperations:
    @pytest.mark.asyncio
    async def test_add_order(self, queue, orders):
        order = next(o for o in orders if o.drinks[0].milk != "No Milk" and len(o.drinks) == 1)
        milk_type = f"{order.drinks[0].milk}_{order.drinks[0].texture}"
        orderID = order.orderID
        
        await queue.addOrder(order, update_db=False)
        
        assert len(queue.orders) == 1
        assert queue.orders[0] == order
        assert 0 in queue.lookupTable[milk_type]
        assert queue.totalDrinks == 1
        assert queue.totalOrders == 1
        assert orderID in queue.orderHistoryIndex.keys()
        assert queue.orderHistoryIndex[orderID]['index'] == 0

    @pytest.mark.asyncio
    async def test_complete_item(self, queue):
        assert queue.orderHistory[0].timeComplete is None
        await queue.completeItem(0)
        assert queue.orderHistory[0].timeComplete is not None
        assert len(queue.orders) == 0
        assert queue.totalOrders == 0
        assert queue.totalDrinks == 0
        assert queue.OrdersComplete == 1
        assert queue.DrinksComplete == 1
        assert all([not v for v in queue.lookupTable.values()])


class TestOrderBatching:
    @pytest.mark.asyncio
    async def test_order_batching(self, 
                            queue, 
                            jeff_order, 
                            hannah_order, 
                            oat_cappuccinos, 
                            soy_cappuccino):
        await queue.addOrder(jeff_order, update_db=False)

        assert jeff_order.orderID in queue.orderHistoryIndex.keys()
        assert queue.orderHistoryIndex[jeff_order.orderID]['index'] == 0

        await queue.addOrder(hannah_order, update_db=False)

        assert hannah_order.orderID in queue.orderHistoryIndex.keys()
        assert queue.orderHistoryIndex[hannah_order.orderID]['index'] == 0
        assert queue.orderHistoryIndex[jeff_order.orderID]['index'] == 1

        assert len(queue.orders) == 3
        assert queue.totalDrinks == 4
        assert queue.totalOrders == 2
        assert isinstance(queue.orders[1], Batch)
        assert all(drink in queue.orders[1].drinks for drink in oat_cappuccinos)
        assert soy_cappuccino in queue.orders[2].drinks
        assert 1 in queue.lookupTable['Oat_Dry']
        assert 2 in queue.lookupTable['Soy_Dry']

    @pytest.mark.asyncio
    async def test_cross_order_batching(self, 
                                  queue, 
                                  adam_order, 
                                  kayleigh_order):
        
        await queue.addOrder(adam_order, update_db=False)
        await queue.addOrder(kayleigh_order, update_db=False)

        print(queue)

        assert len(queue.orders) == 4
        assert queue.totalOrders == 4
        assert queue.totalDrinks == 6
        assert isinstance(queue.orders[-1], Batch)
        assert 3 in queue.lookupTable['Whole_Wet']


class TestCompleteDrinks:
    @pytest.mark.asyncio
    async def test_complete_drinks(self,
                             queue, 
                             soy_cappuccino, 
                             jeff_order,
                             ):
        await queue.completeDrinks([soy_cappuccino.identifier, jeff_order.drinks[0].identifier])

        assert queue.totalDrinks == 4
        assert queue.totalOrders == 3
        assert len(queue.orders) == 2
        assert isinstance(queue.orders[0], Batch)
        assert isinstance(queue.orders[1], Batch)
        assert 1 in queue.lookupTable['Whole_Wet']
        assert 0 in queue.lookupTable['Oat_Dry']
        assert queue.lookupTable['Soy_Dry'] == set()
