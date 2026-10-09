from datetime import date, time
from json import JSONDecodeError, dumps, loads

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from brewflow.domain.models import Drink, Order
from brewflow.persistence.db import Database, Drinks, Orders


def decode_options(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = loads(value)
    except JSONDecodeError:
        return value.split(",")
    if isinstance(decoded, list) and all(isinstance(option, str) for option in decoded):
        return decoded
    return value.split(",")


def drink_from_record(record: Drinks) -> Drink:
    return Drink(
        identifier=record.identifier,
        orderID=record.orderID,
        customer=record.customer,
        drink=record.drink,
        milk=record.milk,
        milk_volume=record.milk_volume,
        shots=record.shots,
        temperature=record.temperature,
        texture=record.texture,
        options=decode_options(record.options),
        timeReceived=record.timeReceived,
        timeComplete=record.timeComplete,
    )


def order_from_record(record: Orders) -> Order:
    return Order(
        orderID=record.orderID,
        customer=record.customer,
        dateReceived=record.dateReceived,
        timeReceived=record.timeReceived,
        timeComplete=record.timeComplete,
        drinks=[drink_from_record(drink) for drink in record.drinks],
    )


class OrderStore:
    def __init__(self, database: Database, session: AsyncSession):
        self.database = database
        self.session = session

    @classmethod
    async def create(cls, uri: str) -> "OrderStore":
        database = Database(uri)
        await database.initialize()
        return cls(database, database.session())

    async def close(self) -> None:
        await self.session.close()
        await self.database.close()

    async def add_order(self, order: Order) -> None:
        if order.dateReceived is None or order.timeReceived is None:
            raise ValueError("Order must be timestamped before persistence")
        try:
            record = Orders(
                orderID=order.orderID,
                customer=order.customer,
                dateReceived=order.dateReceived,
                timeReceived=order.timeReceived,
                timeComplete=order.timeComplete,
            )
            record.drinks = [
                Drinks(
                    identifier=drink.identifier,
                    orderID=order.orderID,
                    customer=drink.customer,
                    drink=drink.drink,
                    milk=drink.milk,
                    milk_volume=drink.milk_volume,
                    shots=drink.shots,
                    temperature=drink.temperature,
                    texture=drink.texture,
                    options=dumps(drink.options, separators=(",", ":")),
                    timeReceived=drink.timeReceived,
                    timeComplete=drink.timeComplete,
                )
                for drink in order.drinks
            ]
            self.session.add(record)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def get_order(self, order_id: str) -> Order | None:
        result = await self.session.execute(
            select(Orders)
            .where(Orders.orderID == order_id)
            .options(selectinload(Orders.drinks))
        )
        record = result.scalar_one_or_none()
        return order_from_record(record) if record else None

    async def drink_identifiers_exist(self, identifiers: set[str]) -> bool:
        if not identifiers:
            return False
        result = await self.session.execute(
            select(Drinks.identifier).where(Drinks.identifier.in_(identifiers)).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def service_orders(self, service_date: date) -> list[Order]:
        result = await self.session.execute(
            select(Orders)
            .where(Orders.dateReceived == service_date)
            .order_by(asc(Orders.timeReceived))
            .options(selectinload(Orders.drinks))
        )
        return [order_from_record(record) for record in result.scalars().all()]

    async def complete_drinks(self, identifiers: set[str], completed_at: time) -> None:
        if not identifiers:
            return
        try:
            result = await self.session.execute(
                select(Drinks)
                .where(Drinks.identifier.in_(identifiers))
                .options(selectinload(Drinks.order).selectinload(Orders.drinks))
            )
            affected_orders: dict[str, Orders] = {}
            for drink in result.scalars().all():
                if drink.timeComplete is None:
                    drink.timeComplete = completed_at
                if drink.order is not None:
                    affected_orders[drink.order.orderID] = drink.order
            for order in affected_orders.values():
                if all(drink.timeComplete is not None for drink in order.drinks):
                    order.timeComplete = completed_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
