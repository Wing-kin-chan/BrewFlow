import pytest
from Manager.app.scripts.orders.queueManager import *
from Menu import Order
from typing import List
from datetime import datetime

@pytest.fixture(scope = 'module')
def queue():
    return Queue()

date = datetime.now().date()
time = datetime.now().time()

# Random drinks, and orders for testing
# Order takes in dictionary rather than instance of Drink
jeff_drink = {
    'orderID': 1,
    'drink': 'double_espresso',
    'milk': 'No milk',
    'milk_volume': 0,
    'shots': 2,
    'temperature': None,
    'texture': None,
    'options': [],
    'customer': 'Jeff'
}

jeff_order = Order.model_validate(
    {'orderID': 1,
     'date': date,
     'time': time,
     'customer': 'Jeff',
     'drinks':[jeff_drink]}
)

kayleigh_drink = {
    'orderID': 2,
    'drink': 'Flat White',
    'milk': 'Full fat',
    'milk_volume': 1,
    'shots': 2,
    'temperature': None,
    'texture': 'Wet',
    'options': [],
    'customer': 'Kayleigh'
}

kayleigh_order = Order.model_validate(
    {'orderID': 2,
     'date': date,
     'time': time,
     'customer': 'Kayleigh',
     'drinks':[kayleigh_drink]}
)

adam_drink = {
    'orderID': 12345,
    'drink': 'Latte',
    'milk': 'Full fat',
    'milk_volume': 2,
    'shots': 2,
    'temperature': None,
    'texture': 'Wet',
    'options': [],
    'customer': 'Adam'
}

adam_order = Order.model_validate(
    {'orderID': 12345,
     'date': date,
     'time': time,
     'customer': 'Adam',
     'drinks':[adam_drink]}
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
        'customer': 'Hannah'
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
        'customer': 'Hannah'
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
        'customer': 'Hannah'
    }
]

hannah_order = Order.model_validate(
    {
    'orderID': 23456,
    'customer': 'Hannah',
    'date': date,
    'time': time,
    'drinks': hannah_drinks
    }
)

martin_drinks = [
    {
        'orderID': 34567,
        'drink': 'Flat White',
        'milk': 'Full fat',
        'shots': 2,
        'milk_volume': 1,
        'temperature': None,
        'texture': 'Wet',
        'options': [],
        'customer': 'Martin'
    },
    {
        'orderID': 34567,
        'drink': 'Double Macchiato',
        'milk': 'Soy',
        'milk_volume': 0.5,
        'shots': 2,
        'temperature': None,
        'texture': 'Dry',
        'options': [],
        'customer': 'Martin'
    }
]

martin_order = Order.model_validate(
    {
        'orderID': 34567,
        'customer': 'Martin',
        'date': date,
        'time': time,
        'drinks': martin_drinks
    }
)

def test_queueInitialization(queue):
    assert hasattr(queue, 'orders')
    assert hasattr(queue, 'totalOrders')
    assert hasattr(queue, 'totalDrinks')
    assert hasattr(queue, 'OrdersComplete')
    assert hasattr(queue, 'DrinksComplete')
    assert hasattr(queue, 'lookupTable')

    assert len(queue.orders) == 0
    assert isinstance(queue.orders, List)
    assert isinstance(queue.totalOrders, int)
    assert isinstance(queue.totalDrinks, int)
    assert isinstance(queue.OrdersComplete, int)
    assert isinstance(queue.DrinksComplete, int)
    assert isinstance(queue.lookupTable, dict)

def test_queueAddOrder(queue):
    queue.addOrder(jeff_order)

    assert len(queue.orders) == 1
    assert queue.totalOrders == 1
    assert queue.totalDrinks == 1
    assert isinstance(queue.orders[0], Order)
    assert queue.orders[0] == jeff_order
    
    queue.addOrder(kayleigh_order)

    assert len(queue.orders) == 2
    assert queue.totalOrders == 2
    assert queue.totalDrinks == 2
    assert isinstance(queue.orders[1], Order)
    assert 1 in queue.lookupTable['Full fat_Wet']

    assert queue.orders[0] == jeff_order
    assert queue.orders[1] == kayleigh_order

def test_queueReorder(queue):
    flat_white = [drink for drink in martin_order.drinks if drink.drink == 'Flat White'][0]
    oat_cappuccinos = [drink for drink in hannah_order.drinks if drink.drink == 'Cappuccino' and drink.milk == 'Oat']
    soy_cappuccino = [drink for drink in hannah_order.drinks if drink.milk == 'Soy'][0]
    soy_macchiato = [drink for drink in martin_order.drinks if drink.drink == 'Double Macchiato'][0]
    latte = [drink for drink in adam_order.drinks if drink.drink == 'Latte'][0]

    queue.addOrder(hannah_order)

    assert len(queue.orders) == 4
    assert queue.totalOrders == 3
    assert queue.totalDrinks == 5
    assert queue.orders[0] == jeff_order
    assert queue.orders[1] == kayleigh_order

    assert isinstance(queue.orders[2], Order)
    assert soy_cappuccino in queue.orders[2].drinks
    assert 2 in queue.lookupTable['Soy_Dry']

    assert isinstance(queue.orders[3], Batch)
    assert all(drink in queue.orders[3].drinks for drink in oat_cappuccinos)
    assert sum(drink.milk_volume for drink in queue.orders[3].drinks) == queue.orders[3].volume
    assert 3 in queue.lookupTable['Oat_Dry']
    
    queue.addOrder(adam_order)

    assert len(queue.orders) == 5
    assert queue.totalOrders == 4
    assert queue.totalDrinks == 6

    assert isinstance(queue.orders[4], Order)
    assert queue.orders[4] == adam_order
    assert 4 in queue.lookupTable['Full fat_Wet']

    queue.addOrder(martin_order)

    assert len(queue.orders) == 5
    assert queue.totalOrders == 5
    assert queue.totalDrinks == 8

    assert isinstance(queue.orders[2], Batch)
    assert soy_cappuccino and soy_macchiato in queue.orders[2].drinks
    assert 2 in queue.lookupTable['Soy_Dry']

    assert isinstance(queue.orders[4], Batch)
    assert flat_white and latte in queue.orders[4].drinks
    assert 4 in queue.lookupTable['Full fat_Wet']
    