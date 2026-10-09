from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator


Temperature = Literal["Warm", "Normal", "Extra Hot"]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Drink(BaseModel):
    orderID: str | None = None
    drink: str
    milk: str
    milk_volume: float = Field(ge=0)
    shots: int = Field(ge=0)
    temperature: Temperature
    texture: str | None = None
    options: list[str] = Field(default_factory=list)
    customer: str | None = None
    identifier: Identifier
    timeReceived: time | None = None
    timeComplete: time | None = None

    @model_validator(mode="after")
    def validate_milk_texture(self) -> Drink:
        if self.milk == "No Milk" and self.texture is not None:
            raise ValueError("Drinks without milk cannot have a milk texture")
        if self.milk != "No Milk" and self.texture is None:
            raise ValueError("Milk drinks require a texture")
        return self

    def __hash__(self) -> int:
        return hash(self.identifier)


class Order(BaseModel):
    orderID: Identifier
    customer: str
    dateReceived: date | None = None
    timeReceived: time | None = None
    timeComplete: time | None = None
    drinks: list[Drink]

    @model_validator(mode="after")
    def populate_drink_ownership(self) -> Order:
        if not self.drinks:
            raise ValueError("An order must contain at least one drink")
        identifiers: set[str] = set()
        for drink in self.drinks:
            if drink.orderID is not None and drink.orderID != self.orderID:
                raise ValueError("Drink orderID must match its parent order")
            if drink.customer is not None and drink.customer != self.customer:
                raise ValueError("Drink customer must match its parent order")
            if drink.identifier in identifiers:
                raise ValueError("Drink identifiers must be unique within an order")
            identifiers.add(drink.identifier)
            drink.orderID = self.orderID
            drink.customer = self.customer
            if drink.timeReceived is None:
                drink.timeReceived = self.timeReceived
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return False
        return (
            self.orderID == other.orderID
            and self.customer == other.customer
            and self.dateReceived == other.dateReceived
            and self.timeReceived == other.timeReceived
            and self.timeComplete == other.timeComplete
            and Counter(self.drinks) == Counter(other.drinks)
        )

    def stamp_received(self, received: datetime) -> None:
        self.dateReceived = received.date()
        self.timeReceived = received.time()
        self.timeComplete = None
        for drink in self.drinks:
            drink.orderID = self.orderID
            drink.customer = self.customer
            drink.timeReceived = received.time()
            drink.timeComplete = None

    def group_drinks(self) -> list[list[Drink]]:
        groups: defaultdict[tuple[str, str | None], list[Drink]] = defaultdict(list)
        for drink in self.drinks:
            if drink.milk != "No Milk":
                groups[(drink.milk, drink.texture)].append(drink)
        return list(groups.values())

    def stable_payload(self) -> dict[str, Any]:
        data = self.model_dump()
        data.pop("dateReceived", None)
        data.pop("timeReceived", None)
        data.pop("timeComplete", None)
        for drink in data["drinks"]:
            drink.pop("timeReceived", None)
            drink.pop("timeComplete", None)
        return data
