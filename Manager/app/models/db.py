from sqlalchemy import ForeignKey, String, Integer, Float, Time, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from typing import List, Optional
from datetime import date, time

class Base(DeclarativeBase):
    pass


class Orders(Base):
    __tablename__ = 'orders'
    
    orderID: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer: Mapped[str] = mapped_column(String)
    dateReceived: Mapped[date] = mapped_column(Date)
    timeReceived: Mapped[time] = mapped_column(Time)
    timeComplete: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    drinks: Mapped[List["Drinks"]] = relationship("Drinks", 
                                                 back_populates="order", 
                                                 cascade="all, delete-orphan")


class Drinks(Base):
    __tablename__ = 'drinks'
    
    identifier: Mapped[str] = mapped_column(String, primary_key=True)
    orderID: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('orders.orderID', ondelete="CASCADE"))
    drink: Mapped[str] = mapped_column(String)
    milk: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    milk_volume: Mapped[float] = mapped_column(Float, nullable = True)
    shots: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    texture: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    options: Mapped[str] = mapped_column(String, nullable = True)
    customer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timeReceived: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    timeComplete: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    order: Mapped[Optional[Orders]] = relationship("Orders", back_populates="drinks")


class Database:
    def __init__(self, URI, engine):
        self.URI = URI
        self.engine = engine

    @classmethod
    async def init_db(cls, URI: str) -> None:
        engine = create_async_engine(URI, echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return cls(URI, engine)

    async def getSession(self) -> AsyncSession:
        async_engine = self.engine
        AsyncSessionLocal = async_sessionmaker(
            async_engine, class_ = AsyncSession, expire_on_commit = False
        )

        return AsyncSessionLocal()
