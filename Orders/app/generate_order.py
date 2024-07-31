from pydantic import BaseModel
from Orders.app.generate_drink import Drink
from datetime import datetime, date, time
from typing import Optional
import requests, random

nameAPI_address = 'https://randomuser.me/api/?results=1&inc=name'

def getCustomerName() -> str|None:
    '''
    Gets a random name from a random user generator API.
    '''
    try:
        response = requests.get(url = nameAPI_address)
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.TooManyRedirects:
        return None
    except requests.exceptions.RequestException:
        return None
    
    if response.status_code == 200:
        try:
            name = response.json()['results'][0]['name']['first']
            return name
        except requests.exceptions.JSONDecodeError:
            return None

class Order(BaseModel):
    customer: str
    date: date
    time: time
    drinks: list[Drink]

    @staticmethod
    def generateOrder():
        customer = getCustomerName()
        now = datetime.now()
        order_date = now.date()
        order_time = now.time()

        seed = random.randint(0, 100)
        
        if 15 < seed < 40:
            drinks = [Drink.generateDrink() for _ in range(0, random.randint(1, 3))]
        if seed < 15:
            drinks = [Drink.generateDrink() for _ in range(0, random.randint(3, 10))]
        else:
            drinks = [Drink.generateDrink()]

        order = Order(customer = customer,
                      date = order_date,
                      time = order_time,
                      drinks = drinks)
        return order