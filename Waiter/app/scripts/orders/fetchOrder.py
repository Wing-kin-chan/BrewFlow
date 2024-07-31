import requests
from pydantic import BaseModel, model_validator
from datetime import date, time
from typing import Optional, List
import json
import logging

logging.basicConfig(level = logging.DEBUG)

orderAPI_endpoint = 'http://127.0.0.1:8000/order'

class Drink(BaseModel):
    drink: str 
    milk: str
    shots: int
    temperature: Optional[str]
    texture: Optional[str]
    options: List[str]
    customer: Optional[str]

class Order(BaseModel):
    customer: str
    date: date
    time: time
    drinks: List[Drink]

    @model_validator(mode = 'before')
    def consistent_drinkOwner(cls, values):
        customer = values.get('customer')
        drinks = values.get('drinks')
        for drink in drinks:
            if 'customer' not in drink or drink['customer'] is None:
                drink['customer'] = customer
        return values

def fetchOrder() -> Order|None:
    '''Returns an order that is randomly generated from the /order HTTP endpoint.'''
    try:
        response = requests.get(orderAPI_endpoint)
    except requests.exceptions.ConnectTimeout as e:
        logging.error(f'Connection timed out: {e}')
        return None
    except requests.exceptions.TooManyRedirects as e:
        logging.error(f'Too many redirects: {e}')
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f'Request error: {e}')
        return None
    
    try:
        data = json.loads(response.json())
    except json.JSONDecodeError as e:
        logging.error(f'JSON Decode error: {e}')
        return None

    order = Order.model_validate(data)

    return order

print(fetchOrder())