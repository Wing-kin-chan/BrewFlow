from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import date, time

class Drink(BaseModel):
    orderID: Optional[int]
    drink: str 
    milk: Optional[str]
    milk_volume: float
    shots: int
    temperature: Optional[str]
    texture: Optional[str]
    options: List[str]
    customer: Optional[str]

    def __repr__(self):
        if self.customer:
            result = f"{self.customer}'s {self.drink}\n"
        else:
            result = f"{self.drink}\n"
        result += f"Shots: {self.shots}\n"
        
        # Add milk information
        milk_info = self.milk if self.milk else "No milk"
        result += f"Milk: {milk_info}\n"
        
        # Add options, each on a new line
        result += "Options:\n"
        if self.options:
            for option in self.options:
                result += f"{option}\n"
        else:
            result += "No options\n"

        return result
    
    def __eq__(self, other):
        if isinstance(other, Drink):
            return self.__dict__ == other.__dict__
        return False
    
    def __hash__(self):
        return hash((self.__dict__))

class Order(BaseModel):
    orderID: int
    customer: str
    date: date
    time: time
    drinks: List[Drink]

    def __repr__(self):
        result = f"OrderID: {self.orderID}\n"
        result += f"      {self.customer}\n"
        result += "      Drinks:\n"
        if self.drinks:
            for drink in self.drinks:
                result += f"      - {drink.drink} with {drink.milk}\n"
        
        return result

    @model_validator(mode = 'before')
    @classmethod
    def check_drinkOwner(cls, values):
        customer = values.get('customer')
        drinks = values.get('drinks', [])
        for drink in drinks:
            if drink.get('customer') is None:
                drink['customer'] = customer
        return values
    
    @model_validator(mode = 'before')
    @classmethod
    def check_drinkOrderID(cls, values):
        orderID = values.get('orderID')
        drinks = values.get('drinks', [])
        for drink in drinks:
            if drink.get('orderID') is None:
                drink['orderID'] = orderID
        return values