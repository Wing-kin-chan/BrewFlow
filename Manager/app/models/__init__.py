from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import date, time
from collections import defaultdict, Counter

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
    identifier: int = Field(default_factory = lambda: 0, init = False)
    timeReceived: Optional[time]
    timeComplete: Optional[time]

    def __init__(self, **data):
        super().__init__(**data)
        if not data.get('identifier'):
            object.__setattr__(self, 'identifier', id(self))

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        if isinstance(other, Drink):
            return(
                self.orderID == other.orderID and
                self.drink == other.drink and
                self.milk == other.milk and
                self.milk_volume == other.milk_volume and
                self.shots == other.shots and
                self.temperature == other.temperature and
                self.texture == other.texture and
                self.options == other.options and
                self.customer == other.customer and
                self.identifier == other.identifier and
                self.timeReceived == other.timeReceived and
                self.timeComplete == other.timeComplete
                   )
        return False

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

class Order(BaseModel):
    orderID: int
    customer: str
    dateReceived: date
    timeReceived: time
    timeComplete: Optional[time]
    drinks: List[Drink]

    def __repr__(self):
        result = f"OrderID: {self.orderID}\n"
        result += f"      {self.customer}\n"
        result += "      Drinks:\n"
        if self.drinks:
            for drink in self.drinks:
                result += f"      - {drink.drink} with {drink.milk}\n"
        
        return result
    
    def __eq__(self, other):
        if isinstance(other, Order):
            return(
                self.orderID == other.orderID and
                self.customer == other.customer and
                self.dateReceived == other.dateReceived and
                self.timeReceived == other.timeReceived and
                self.timeComplete == other.timeComplete and
                Counter(self.drinks) == Counter(other.drinks)
            )
        return False

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
    
    @model_validator(mode = 'before')
    @classmethod
    def check_drinkTime(cls, values):
        order_time = values.get('timeReceived')
        drinks = values.get('drinks', [])
        for drink in drinks:
            if drink.get('timeReceived') is None:
                drink['timeReceived'] = order_time
        return values

    def group_drinks(self) -> List[List[Drink]]:
        drink_groups = defaultdict(list)

        for drink in self.drinks:
            if drink.milk:
                key = (drink.milk, drink.texture)
                drink_groups[key].append(drink)
        
        return list(drink_groups.values())
    