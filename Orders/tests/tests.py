import pytest
from tqdm import trange
from fastapi.testclient import TestClient
from Orders.app.generate_drink import *
from Orders.app.generate_order import *
from Orders.config.options import *
from Orders.main import app
from datetime import date, time
import json

client = TestClient(app)

def test_generateDrink():
    drink = Drink.generateDrink()
    assert hasattr(drink, 'drink')
    assert hasattr(drink, 'milk')
    assert hasattr(drink, 'texture')
    assert hasattr(drink, 'shots')
    assert hasattr(drink, 'temperature')
    assert drink.drink in list(DRINKS.keys())
    assert drink.milk in MILKS
    assert drink.texture in TEXTURES
    assert drink.temperature in TEMPERATURES
    assert all(option in OPTIONS for option in drink.options)
    assert isinstance(drink.shots, int)

def test_random_drink_generation(capsys):
    with capsys.disabled():
        drinks = [Drink.generateDrink() for _ in range(0, 1000)]

    drink_types = set(drink.drink for drink in drinks)
    assert len(drink_types) > 1

    for drink in drinks:
        assert hasattr(drink, 'drink')
        assert hasattr(drink, 'milk')
        assert hasattr(drink, 'texture')
        assert hasattr(drink, 'shots')
        assert hasattr(drink, 'temperature')
        assert drink.drink in list(DRINKS.keys())
        assert drink.milk in MILKS
        assert drink.texture in TEXTURES
        assert drink.temperature in TEMPERATURES
        assert all(option in OPTIONS for option in drink.options)
        assert isinstance(drink.shots, int)
    
def test_getCustomerName():
    name = getCustomerName()
    assert isinstance(name, str)

def test_random_name_generation(capsys):
    with capsys.disabled():
        names = [getCustomerName() for _ in trange(0, 50)]

    unique_names = set(names)
    assert len(unique_names) > 1
    assert all(isinstance(name, str) for name in unique_names)

def test_generateOrder():
    order = Order.generateOrder()
    assert hasattr(order, 'customer')
    assert hasattr(order, 'date')
    assert hasattr(order, 'time')
    assert hasattr(order, 'drinks')
    assert isinstance(order.customer, str)
    assert isinstance(order.date, date)
    assert isinstance(order.time, time)
    assert isinstance(order.drinks, list)
    assert all(isinstance(drink, Drink) for drink in order.drinks)
    
    for drink in order.drinks:
        assert hasattr(drink, 'drink')
        assert hasattr(drink, 'milk')
        assert hasattr(drink, 'texture')
        assert hasattr(drink, 'shots')
        assert hasattr(drink, 'temperature')
        assert drink.drink in list(DRINKS.keys())
        assert drink.milk in MILKS
        assert drink.texture in TEXTURES
        assert drink.temperature in TEMPERATURES
        assert all(option in OPTIONS for option in drink.options)
        assert isinstance(drink.shots, int)

def test_random_order_generation(capsys):
    with capsys.disabled():
        orders = [Order.generateOrder() for _ in trange(0, 50)]
    
    for order in orders:
        assert hasattr(order, 'customer')
        assert hasattr(order, 'date')
        assert hasattr(order, 'time')
        assert hasattr(order, 'drinks')
        assert isinstance(order.customer, str)
        assert isinstance(order.date, date)
        assert isinstance(order.time, time)
        assert isinstance(order.drinks, list)
        assert all(isinstance(drink, Drink) for drink in order.drinks)

        for drink in order.drinks:
            assert hasattr(drink, 'drink')
            assert hasattr(drink, 'milk')
            assert hasattr(drink, 'texture')
            assert hasattr(drink, 'shots')
            assert hasattr(drink, 'temperature')
            assert drink.drink in list(DRINKS.keys())
            assert drink.milk in MILKS
            assert drink.texture in TEXTURES
            assert drink.temperature in TEMPERATURES
            assert all(option in OPTIONS for option in drink.options)
            assert isinstance(drink.shots, int)
    
def test_getOrder():
    response = client.get('/order')
    assert response.status_code == 200
    data = json.loads(response.json())

    assert 'customer' in data
    assert 'date' in data
    assert 'time' in data
    assert 'drinks' in data
    assert isinstance(data['customer'], str)
    assert isinstance(data['date'], str)
    assert isinstance(data['time'], str)
    assert isinstance(data['drinks'], list)

    for drink in data['drinks']:
        assert "drink" in drink
        assert "milk" in drink
        assert "shots" in drink
        assert "texture" in drink
        assert "temperature" in drink
        assert "options" in drink
        
        assert isinstance(drink["drink"], str)
        assert isinstance(drink["milk"], str)
        assert isinstance(drink["shots"], int)
        assert isinstance(drink["texture"], str) or drink["texture"] is None
        assert isinstance(drink["temperature"], str)
        assert isinstance(drink["options"], list)

    