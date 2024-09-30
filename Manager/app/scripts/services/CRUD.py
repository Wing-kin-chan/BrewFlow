from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc, text

from Manager.app.models.db import Orders, Drinks, Database, AsyncSession
from Manager.app.scripts.services import PydanticORM

from Menu import Order
from typing import List
from datetime import time


class Connection:
    def __init__(self, session):
        self.session: AsyncSession = session

    @classmethod
    async def new(cls, URI: str):
        db: Database = await Database.init_db(URI)
        session = await db.getSession()
        return cls(session)
    
    async def close(self):
        await self.session.close()

    async def addOrder(self, order: Order) -> None:
        '''Adds an order and its drinks to the database'''
        try:
            db_order = Orders(
                orderID = order.orderID,
                customer = order.customer,
                dateReceived = order.dateReceived,
                timeReceived = order.timeReceived 
            )
            self.session.add(db_order)

            for drink in order.drinks:
                db_drink = Drinks(
                    orderID = order.orderID,
                    drink = drink.drink,
                    milk = drink.milk,
                    milk_volume = drink.milk_volume,
                    shots = drink.shots,
                    temperature = drink.temperature,
                    texture = drink.texture,
                    options = ','.join(drink.options),
                    identifier = drink.identifier,
                    timeReceived = drink.timeReceived,
                )
                self.session.add(db_drink)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            raise e
        

    async def completeOrder(self, orderID: int, time: time) -> None:
        '''Updates the timeComplete field for an order record with the respective orderID'''
        try:
            query = select(Orders).where(Orders.orderID == orderID)
            result = await self.session.execute(query)
            order = result.scalar_one_or_none()

            if order:
                order.timeComplete = time
                await self.session.commit()
        
        except Exception as e:
            await self.session.rollback()
            raise e

    async def completeDrink(self, identifier: int, time: time) -> None:
        '''Updates the timeComplete field for the drink record with the respective identifier'''
        try:
            query = select(Drinks).where(Drinks.identifier == identifier)
            result = await self.session.execute(query)
            drink = result.scalar_one_or_none()

            if drink:
                drink.timeComplete = time
                await self.session.commit()
        
        except Exception as e:
            await self.session.rollback()
            raise e


    async def getQueue(self) -> List[Order]:
        '''
        This function returns a list of order objects and their respective drinks.
        '''
        
        query = (
            select(Orders)
            .options(selectinload(Orders.drinks))
            .order_by(desc(Orders.timeReceived))
        )
        result = await self.session.execute(query)

        orders = result.scalars().all()
        queue: List[Order] = []
        
        for obj in orders:
            queue.append(PydanticORM.readOrdersORM(obj))
        return queue
    

    async def clearQueue(self) -> None:
        '''Clears all records from local storage'''
        try:
            await self.session.execute(text("DELETE FROM drinks"))
            await self.session.execute(text("DELETE FROM orders"))
            await self.session.commit()
        
        except Exception as e:
            await self.session.rollback()
            raise e
