import pytest
from datetime import date, time
from Manager.app.scripts.orders import fetchOrder

def test_fetchOrders():
    order = fetchOrder.fetchOrder()
    assert hasattr(order, 'orderID')
    assert hasattr(order, 'customer')
    assert hasattr(order, 'date')
    assert hasattr(order, 'time')
    assert hasattr(order, 'drinks')

    assert isinstance(order.orderID, int)
    assert isinstance(order.customer, str)
    assert isinstance(order.date, date)
    assert isinstance(order.time, time)
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
        