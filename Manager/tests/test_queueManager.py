import pytest
from typing import List
from tqdm import trange
from datetime import datetime
import logging, copy, sys

from Manager.app.scripts.queueManager import Queue, Batch
from Manager.app.scripts.queueManager import fetchOrder
from Menu import Order

@pytest.fixture(scope = 'module')
def queue():
    return Queue()

def pytest_configure(config):
    logging.basicConfig(level = logging.INFO)

def is_all_empty_except_keys(dictionary: dict, except_keys: list):
    for k, v in dictionary.items():
        if k not in except_keys and v:
            return False
    return True

# Random drinks, and orders for testing
logging.info("Generating random orders")
orders = [fetchOrder.fetchOrder() for _ in trange(0, 50, file = sys.stdout)]

date = datetime.now().date()
time = datetime.now().time()

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

jeff_order = Order.model_validate(
    {'orderID': 1,
     'date': date,
     'timeReceived': time,
     'customer': 'Jeff',
     'drinks':[jeff_drink],
     'timeComplete': None}
)

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

kayleigh_order = Order.model_validate(
    {'orderID': 2,
     'date': date,
     'timeReceived': time,
     'customer': 'Kayleigh',
     'drinks':[kayleigh_drink],
     'timeComplete': None}
)

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

adam_order = Order.model_validate(
    {'orderID': 12345,
     'date': date,
     'timeReceived': time,
     'customer': 'Adam',
     'drinks':[adam_drink],
     'timeComplete': None}
)

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

hannah_order = Order.model_validate(
    {
    'orderID': 23456,
    'customer': 'Hannah',
    'date': date,
    'timeReceived': time,
    'drinks': hannah_drinks,
    'timeComplete': None
    }
)

oat_cappuccinos = [drink for drink in hannah_order.drinks if drink.drink == 'Cappuccino' and drink.milk == 'Oat']
soy_cappuccino = [drink for drink in hannah_order.drinks if drink.milk == 'Soy'][0]
latte = [drink for drink in adam_order.drinks if drink.drink == 'Latte'][0]
flat_white = [drink for drink in kayleigh_order.drinks if drink.drink == 'Flat White'][0]

def test_queueInitialization(queue):
    assert hasattr(queue, 'orders')
    assert hasattr(queue, 'totalOrders')
    assert hasattr(queue, 'totalDrinks')
    assert hasattr(queue, 'OrdersComplete')
    assert hasattr(queue, 'DrinksComplete')
    assert hasattr(queue, 'lookupTable')
    assert hasattr(queue, 'orderHistory')

    assert len(queue.orders) == 0
    assert isinstance(queue.orders, List)
    assert isinstance(queue.orderHistory, List)
    assert isinstance(queue.totalOrders, int)
    assert isinstance(queue.totalDrinks, int)
    assert isinstance(queue.OrdersComplete, int)
    assert isinstance(queue.DrinksComplete, int)
    assert isinstance(queue.lookupTable, dict)

def test_queueAddOrder(queue):
    order = [o for o in orders if o.drinks[0].milk != "No Milk" and
             len(o.drinks) == 1][0]
    milk_type = f"{order.drinks[0].milk}_{order.drinks[0].texture}"
    queue.addOrder(order)

    assert len(queue.orders) == 1
    assert len(queue.orderHistory) == 1
    assert queue.totalOrders == 1
    assert queue.totalDrinks == 1
    assert isinstance(queue.orders[0], Order)
    assert isinstance(queue.orderHistory[0], Order)
    assert queue.orders[0] == order
    assert queue.orderHistory[0] == order
    assert 0 in queue.lookupTable[milk_type]

def test_queueCompleteItem(queue):
    assert queue.orderHistory[0].timeComplete is None
    assert queue.orderHistory[0].drinks[0].timeComplete is None

    queue.completeItem(0)

    assert queue.orderHistory[0].timeComplete is not None
    assert queue.orderHistory[0].drinks[0].timeComplete is not None
    assert len(queue.orders) == 0
    assert queue.totalOrders == 0
    assert queue.totalDrinks == 0
    assert all(not value for value in queue.lookupTable.values())

def test_orderBatching(queue):
    queue.addOrder(jeff_order)

    assert len(queue.orders) == 1
    assert queue.totalDrinks == 1
    assert queue.totalOrders == 1
    assert isinstance(queue.orders[0], Order)
    assert queue.orders[0] == jeff_order
    assert queue.orderHistory[0] == jeff_order

    queue.addOrder(kayleigh_order)
    assert len(queue.orders) == 2
    assert queue.totalDrinks == 2
    assert queue.totalOrders == 2
    assert isinstance(queue.orders[1], Order)
    assert queue.orders[1] == kayleigh_order
    assert queue.orderHistory[0] == kayleigh_order

    global hannah_order_copy
    hannah_order_copy = copy.deepcopy(hannah_order)
    queue.addOrder(hannah_order)
    assert len(queue.orders) == 4
    assert queue.totalDrinks == 5
    assert queue.totalOrders == 3
    assert isinstance(queue.orders[2], Batch)
    assert all(drink in queue.orders[2].drinks for drink in oat_cappuccinos)
    assert 2 in queue.lookupTable['Oat_Dry']
    assert isinstance(queue.orders[3], Order)
    assert soy_cappuccino in queue.orders[3].drinks
    assert 3 in queue.lookupTable['Soy_Dry']
    assert queue.orderHistory[0] == hannah_order_copy

def test_completeDrinks(queue):
    global jeff_order_copy
    jeff_order_copy = copy.deepcopy(jeff_order)

    queue.completeDrinks([soy_cappuccino.identifier, jeff_order.drinks[0].identifier])
    if all([queue.orderHistory[0].drinks[2].timeComplete, 
           queue.orderHistory[2].drinks[0].timeComplete,
           queue.orderHistory[2].timeComplete]):
        queue.orderHistory[0].drinks[2].timeComplete = time
        queue.orderHistory[2].drinks[0].timeComplete = time
        queue.orderHistory[2].timeComplete = time
    else:
        raise ValueError('Completed Items have NoneType timeComplete Attribute')
    
    assert queue.totalDrinks == 3
    assert queue.totalOrders == 2

    assert isinstance(queue.orders[0], Order)
    assert isinstance(queue.orders[1], Batch)
    assert queue.orders[0] == kayleigh_order
    assert all(drink in queue.orders[1].drinks for drink in oat_cappuccinos)
    assert 0 in queue.lookupTable["Whole_Wet"]
    assert 1 in queue.lookupTable["Oat_Dry"]
    assert not queue.lookupTable["Soy_Dry"]

def test_getCompleteItems(queue):
    completed_items = queue.getCompletedItems()

    jeff_order_copy.timeComplete = time
    jeff_order_copy.drinks[0].timeComplete = time
    soy_cappuccino.timeComplete = time
    hannah_order_copy.drinks = [soy_cappuccino]

    assert completed_items[0] == hannah_order_copy
    assert completed_items[1] == jeff_order_copy

def test_crossOrderBatching(queue):
    kayleigh_order_copy = copy.deepcopy(kayleigh_order)
    kayleigh_order_copy_2 = copy.deepcopy(kayleigh_order_copy)

    queue.completeItem(0)
    queue.completeItem(0)

    assert queue.totalDrinks == 0
    assert queue.totalOrders == 0
    assert len(queue.orders) == 0
    assert all(not value for value in queue.lookupTable.values())

    black_coffees = [o for o in orders if o.drinks and o.drinks[0].milk == "No Milk" and
             len(o.drinks) == 1]
    num_orders = len(black_coffees)
    for order in black_coffees:
        queue.addOrder(order)
    assert len(queue.orders) == num_orders
    assert queue.totalOrders == num_orders
    assert queue.totalDrinks == num_orders

    queue.addOrder(adam_order)
    assert isinstance(queue.orders[-1], Order)
    assert queue.orders[-1] == adam_order
    assert queue.orderHistory[0] == adam_order
    assert len(queue.orders) == num_orders + 1
    assert queue.totalDrinks == num_orders + 1
    assert queue.totalOrders == num_orders + 1
    assert num_orders in queue.lookupTable["Whole_Wet"]

    queue.addOrder(kayleigh_order_copy)
    assert isinstance(queue.orders[-1], Batch)
    assert queue.orderHistory[0] == kayleigh_order_copy_2
    assert latte and flat_white in queue.orders[-1].drinks
    assert len(queue.orders) == num_orders + 1
    assert queue.totalDrinks == num_orders + 2
    assert queue.totalOrders == num_orders + 2
    assert num_orders in queue.lookupTable["Whole_Wet"]
    assert is_all_empty_except_keys(queue.lookupTable, ["Whole_Wet"])

def test_edgeCases(queue, capsys):
    with capsys.disabled():
        queue_prior = queue
        queue_next = queue
        for order in orders:
            copy_order = copy.deepcopy(order)
            try:
                queue_next.addOrder(copy_order)
                assert all(order.drinks for order in queue_next.orders)
                queue_prior = queue_next
            except Exception as e:
                logging.error(f"Error: {e}")
                logging.error(f"Queue Prior State: \n {queue_prior}")
                logging.error(f"Adding order: \n {order}")
                logging.error(f"Queue State On addOrder: \n {queue_next}")
                raise Exception(e)
