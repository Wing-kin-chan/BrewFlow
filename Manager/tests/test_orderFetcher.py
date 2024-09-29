import pytest
from datetime import date, time
from Manager.app.scripts.queueManager import fetchOrder

def test_fetchOrders():
    order = fetchOrder.fetchOrder()
    assert hasattr(order, 'orderID')
    assert hasattr(order, 'customer')
    assert hasattr(order, 'dateReceived')
    assert hasattr(order, 'timeReceived')
    assert hasattr(order, 'timeComplete')
    assert hasattr(order, 'drinks')

    assert isinstance(order.orderID, int)
    assert isinstance(order.customer, str)
    assert isinstance(order.dateReceived, date)
    assert isinstance(order.timeReceived, time)
    assert not order.timeComplete
    assert isinstance(order.drinks, list)

    orderID = order.orderID
    orderOwner = order.customer
    for drink in order.drinks:
        assert hasattr(drink, 'orderID')
        assert hasattr(drink, 'customer')
        assert hasattr(drink, 'drink')
        assert hasattr(drink, 'milk')
        assert hasattr(drink, 'shots')
        assert hasattr(drink, 'temperature')
        assert hasattr(drink, 'texture')
        assert hasattr(drink, 'options')
        assert hasattr(drink, 'timeReceived')
        assert hasattr(drink, 'timeComplete')

        assert drink.orderID == orderID
        assert drink.customer == orderOwner

        assert isinstance(drink.orderID, int)
        assert isinstance(drink.customer, str)
        assert isinstance(drink.drink, str)
        assert isinstance(drink.milk, str)
        assert isinstance(drink.shots, int)
        assert isinstance(drink.temperature, str)
        assert isinstance(drink.texture, str) or drink.texture is None
        assert isinstance(drink.options, list)
        assert all(isinstance(option, str) for option in drink.options)
        assert isinstance(drink.timeReceived, time)
        assert not drink.timeComplete