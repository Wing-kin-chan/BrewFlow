import pytest
from tqdm import trange
from fastapi.testclient import TestClient
from datetime import date, time
from typing import List
import json, os

from Orders.app.generate_drink import generateDrink
from Orders.app.generate_order import generateOrder, getCustomerName
from Menu import Order, Drink
from Orders.main import app

client = TestClient(app)

RELATIVE_PATH = "../../Menu/"
MENU_FILE_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH, "menu.json"
)

with open(MENU_FILE_PATH, 'r') as f:
    data = json.load(f)
MILKS: List[str] = data.get('milks', [])
TEXTURES: List[str] = data.get('textures', [])
DRINKS: List[dict] = data.get('drinks', [])
OPTIONS: List[str] = data.get('options', [])
MILKS.append('No Milk')
TEXTURES.append(None)

def test_generateDrink():
    drink = Drink.model_validate(generateDrink())
    assert hasattr(drink, 'drink')
    assert hasattr(drink, 'milk')
    assert hasattr(drink, 'texture')
    assert hasattr(drink, 'shots')
    assert hasattr(drink, 'temperature')
    assert hasattr(drink, 'milk_volume')
    assert hasattr(drink, 'timeReceived')
    assert hasattr(drink, 'timeComplete')
    assert drink.drink in [drink['drink'] for drink in DRINKS]
    assert drink.milk in MILKS
    assert drink.texture in TEXTURES
    assert drink.temperature in ['Extra Hot', 'Normal', 'Warm']
    assert all(option in OPTIONS for option in drink.options)
    assert isinstance(drink.shots, int)
    assert isinstance(drink.milk_volume, float)

def test_random_drink_generation(capsys):
    with capsys.disabled():
        drinks = [Drink.model_validate(generateDrink()) for _ in range(0, 1000)]

    drink_types = set(drink.drink for drink in drinks)
    assert len(drink_types) > 1

    for drink in drinks:
        assert hasattr(drink, 'drink')
        assert hasattr(drink, 'milk')
        assert hasattr(drink, 'texture')
        assert hasattr(drink, 'shots')
        assert hasattr(drink, 'temperature')
        assert hasattr(drink, 'milk_volume')
        assert drink.drink in [drink['drink'] for drink in DRINKS]
        assert drink.milk in MILKS
        assert drink.texture in TEXTURES
        assert drink.temperature in ['Extra Hot', 'Normal', 'Warm']
        assert all(option in OPTIONS for option in drink.options)
        assert isinstance(drink.shots, int)
        assert isinstance(drink.milk_volume, float)
    
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
    order = generateOrder()
    assert hasattr(order, 'orderID')
    assert hasattr(order, 'customer')
    assert hasattr(order, 'date')
    assert hasattr(order, 'timeReceived')
    assert hasattr(order, 'timeComplete')
    assert hasattr(order, 'drinks')
    assert isinstance(order.orderID, int)
    assert isinstance(order.customer, str)
    assert isinstance(order.date, date)
    assert isinstance(order.timeReceived, time)
    assert not order.timeComplete
    assert isinstance(order.drinks, list)
    assert all(isinstance(drink, Drink) for drink in order.drinks)
    
    for drink in order.drinks:
        assert hasattr(drink, 'drink')
        assert hasattr(drink, 'milk')
        assert hasattr(drink, 'texture')
        assert hasattr(drink, 'shots')
        assert hasattr(drink, 'temperature')
        assert drink.drink in [drink['drink'] for drink in DRINKS]
        assert drink.milk in MILKS
        assert drink.texture in TEXTURES
        assert drink.temperature in ['Extra Hot', 'Normal', 'Warm']
        assert all(option in OPTIONS for option in drink.options)
        assert isinstance(drink.shots, int)

def test_random_order_generation(capsys):
    with capsys.disabled():
        orders = [generateOrder() for _ in trange(0, 50)]
    
    for order in orders:
        assert hasattr(order, 'orderID')
        assert hasattr(order, 'customer')
        assert hasattr(order, 'date')
        assert hasattr(order, 'timeReceived')
        assert hasattr(order, 'timeComplete')
        assert hasattr(order, 'drinks')
        assert isinstance(order.orderID, int)
        assert isinstance(order.customer, str)
        assert isinstance(order.date, date)
        assert isinstance(order.timeReceived, time)
        assert not order.timeComplete
        assert isinstance(order.drinks, list)
        assert all(isinstance(drink, Drink) for drink in order.drinks)

        for drink in order.drinks:
            assert hasattr(drink, 'drink')
            assert hasattr(drink, 'milk')
            assert hasattr(drink, 'texture')
            assert hasattr(drink, 'shots')
            assert hasattr(drink, 'temperature')
            assert hasattr(drink, 'timeReceived')
            assert hasattr(drink, 'timeComplete')
            assert drink.drink in [drink['drink'] for drink in DRINKS]
            assert drink.milk in MILKS
            assert drink.texture in TEXTURES
            assert drink.temperature in ['Extra Hot', 'Normal', 'Warm']
            assert all(option in OPTIONS for option in drink.options)
            assert isinstance(drink.shots, int)
    
def test_getOrder():
    response = client.get('/random_order')
    assert response.status_code == 200
    data = json.loads(response.json())

    assert 'customer' in data
    assert 'date' in data
    assert 'timeReceived' in data
    assert 'timeComplete' in data
    assert 'drinks' in data
    assert isinstance(data['customer'], str)
    assert isinstance(data['date'], str)
    assert isinstance(data['timeReceived'], str)
    assert not data['timeComplete']
    assert isinstance(data['drinks'], list)

    for drink in data['drinks']:
        assert "drink" in drink
        assert "milk" in drink
        assert "shots" in drink
        assert "texture" in drink
        assert "temperature" in drink
        assert "options" in drink
        assert "timeReceived" in drink
        assert "timeComplete" in drink
        
        assert isinstance(drink["drink"], str)
        assert isinstance(drink["milk"], str)
        assert isinstance(drink["shots"], int)
        assert isinstance(drink["texture"], str) or drink["texture"] is None
        assert isinstance(drink["temperature"], str)
        assert isinstance(drink["options"], list)
        assert isinstance(drink["timeReceived"], str)
        assert not drink["timeComplete"]
