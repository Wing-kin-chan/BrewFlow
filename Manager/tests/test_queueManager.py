import pytest
from datetime import datetime
import logging
import sys
from tqdm import trange

from Manager.app.scripts.queueManager import Queue, Batch, fetchOrder
from Menu import Order, Drink

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
    jeff_drink = {
        'orderID': 1,
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
        'orderID': 1,
        'date': date,
        'timeReceived': time,
        'customer': 'Jeff',
        'drinks': [jeff_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def kayleigh_order(date_time):
    date, time = date_time
    kayleigh_drink = {
        'orderID': 2,
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
        'orderID': 2,
        'date': date,
        'timeReceived': time,
        'customer': 'Kayleigh',
        'drinks': [kayleigh_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def adam_order(date_time):
    date, time = date_time
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
        'date': date,
        'timeReceived': time,
        'customer': 'Adam',
        'drinks': [adam_drink],
        'timeComplete': None
    })

@pytest.fixture(scope='session')
def hannah_order(date_time):
    date, time = date_time
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
        'date': date,
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
        assert isinstance(queue.orders, list)
        assert isinstance(queue.totalOrders, int)
        assert isinstance(queue.totalDrinks, int)
        assert isinstance(queue.lookupTable, dict)


class TestQueueOperations:
    def test_add_order(self, queue, orders):
        order = next(o for o in orders if o.drinks[0].milk != "No Milk" and len(o.drinks) == 1)
        milk_type = f"{order.drinks[0].milk}_{order.drinks[0].texture}"
        
        queue.addOrder(order)
        
        assert len(queue.orders) == 1
        assert queue.orders[0] == order
        assert 0 in queue.lookupTable[milk_type]

    def test_complete_item(self, queue):
        assert queue.orderHistory[0].timeComplete is None
        queue.completeItem(0)
        assert queue.orderHistory[0].timeComplete is not None
        assert len(queue.orders) == 0


class TestOrderBatching:
    def test_order_batching(self, 
                            queue, 
                            jeff_order, 
                            hannah_order, 
                            oat_cappuccinos, 
                            soy_cappuccino):
        queue.addOrder(jeff_order)
        queue.addOrder(hannah_order)

        assert len(queue.orders) == 3
        assert queue.totalDrinks == 4
        assert isinstance(queue.orders[1], Batch)
        assert all(drink in queue.orders[1].drinks for drink in oat_cappuccinos)
        assert soy_cappuccino in queue.orders[2].drinks
        assert 1 in queue.lookupTable['Oat_Dry']
        assert 2 in queue.lookupTable['Soy_Dry']

    def test_cross_order_batching(self, 
                                  queue, 
                                  adam_order, 
                                  kayleigh_order):
        queue.addOrder(adam_order)
        queue.addOrder(kayleigh_order)

        assert len(queue.orders) == 4
        assert queue.totalOrders == 4
        assert queue.totalDrinks == 6
        assert isinstance(queue.orders[-1], Batch)
        assert 3 in queue.lookupTable['Whole_Wet']


class TestCompleteDrinks:
    def test_complete_drinks(self,
                             queue, 
                             soy_cappuccino, 
                             jeff_order,
                             ):
        queue.completeDrinks([soy_cappuccino.identifier, jeff_order.drinks[0].identifier])
        assert queue.totalDrinks == 4
        assert queue.totalOrders == 3
        assert len(queue.orders) == 2
        assert isinstance(queue.orders[0], Batch)
        assert isinstance(queue.orders[1], Batch)
