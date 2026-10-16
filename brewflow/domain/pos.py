from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from brewflow.domain.models import Drink, Temperature


OptionInput = Annotated[str, Field(min_length=1, max_length=64)]


class CheckoutItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: UUID
    catalogItemID: str = Field(min_length=1, max_length=64)
    milk: str = Field(min_length=1, max_length=64)
    texture: str | None = Field(default=None, max_length=64)
    temperature: Temperature
    options: list[OptionInput] = Field(default_factory=list, max_length=16)


class PosOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orderID: UUID
    customer: str | None = Field(default=None, max_length=100)
    items: list[CheckoutItemInput] = Field(min_length=1, max_length=50)

    @field_validator("customer")
    @classmethod
    def normalize_customer(cls, value: str | None) -> str:
        normalized = (value or "").strip()
        return normalized or "Customer"


class CatalogItemResponse(BaseModel):
    id: str
    name: str
    priceMinor: int
    milkVolume: float
    shots: int
    texture: str | None


class CatalogResponse(BaseModel):
    currency: Literal["gbp"]
    group: Literal["Drinks"] = "Drinks"
    items: list[CatalogItemResponse]
    milks: list[str]
    textures: list[str]
    options: list[str]
    milkSurchargesMinor: dict[str, int]


class PricedItem(BaseModel):
    identifier: str
    catalogItemID: str
    name: str
    unitAmountMinor: int
    milk: str
    texture: str | None
    temperature: Temperature
    options: list[str]


class CanonicalPosItem(BaseModel):
    identifier: str
    catalogItemID: str
    name: str
    unitAmountMinor: int
    drink: Drink

    def public(self) -> PricedItem:
        return PricedItem(
            identifier=self.identifier,
            catalogItemID=self.catalogItemID,
            name=self.name,
            unitAmountMinor=self.unitAmountMinor,
            milk=self.drink.milk,
            texture=self.drink.texture,
            temperature=self.drink.temperature,
            options=list(self.drink.options),
        )


class CanonicalPosOrder(BaseModel):
    orderID: str
    customer: str
    currency: Literal["gbp"]
    totalMinor: int
    items: list[CanonicalPosItem]


class CheckoutResponse(BaseModel):
    orderID: str
    status: Literal["pending_payment", "paid", "queued"]
    currency: Literal["gbp"]
    totalMinor: int
    items: list[PricedItem]
    isDemo: bool
    demoBlocked: bool = False
    stripeSessionID: str | None
    checkoutURL: str | None


class ReceiptResponse(BaseModel):
    orderID: str
    customer: str
    status: Literal["pending_payment", "paid", "queued"]
    checkoutStatus: Literal["creating", "open", "paid", "expired", "failed"]
    currency: Literal["gbp"]
    totalMinor: int
    items: list[PricedItem]
    createdAt: datetime
    paidAt: datetime | None
    queuedAt: datetime | None
    isDemo: bool
    demoBlocked: bool = False


class DemoModeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demoModeEnabled: bool


class DemoModeResponse(BaseModel):
    demoModeEnabled: bool
    demoModePersisted: bool
    demoModeAvailable: bool
