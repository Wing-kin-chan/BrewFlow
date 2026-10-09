from copy import deepcopy
from datetime import date, time
import random

from fastapi.testclient import TestClient

from Orders.app import generate_order
from Orders.app.generate_drink import DRINKS, generateDrink
from Orders.main import app
from brewflow.domain.models import Drink, Order


def test_drink_generation_does_not_mutate_shared_menu():
    before = deepcopy(DRINKS)
    random.seed(7)
    drinks = [Drink.model_validate(generateDrink()) for _ in range(20)]

    assert DRINKS == before
    assert len({drink.drink for drink in drinks}) > 1
    assert all(drink.identifier for drink in drinks)
    assert len({drink.identifier for drink in drinks}) == len(drinks)


def test_order_generation_is_offline_when_name_source_is_stubbed(monkeypatch):
    monkeypatch.setattr(generate_order, "getCustomerName", lambda: "Ada")
    random.seed(3)

    order = generate_order.generateOrder()

    assert isinstance(order, Order)
    assert order.customer == "Ada"
    assert isinstance(order.dateReceived, date)
    assert isinstance(order.timeReceived, time)
    assert order.drinks


def test_random_order_endpoint_returns_an_order(monkeypatch):
    monkeypatch.setattr(generate_order, "getCustomerName", lambda: "Ada")
    monkeypatch.setattr("Orders.main.generateOrder", generate_order.generateOrder)
    random.seed(4)

    response = TestClient(app).get("/random_order")

    assert response.status_code == 200
    assert response.json()["customer"] == "Ada"
    assert isinstance(response.json()["drinks"], list)
