from datetime import date, time
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Time
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Orders(Base):
    __tablename__ = "orders"

    orderID: Mapped[str] = mapped_column(String, primary_key=True)
    customer: Mapped[str] = mapped_column(String)
    dateReceived: Mapped[date] = mapped_column(Date)
    timeReceived: Mapped[time] = mapped_column(Time)
    timeComplete: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    drinks: Mapped[list["Drinks"]] = relationship(
        "Drinks", back_populates="order", cascade="all, delete-orphan"
    )


class Drinks(Base):
    __tablename__ = "drinks"

    identifier: Mapped[str] = mapped_column(String, primary_key=True)
    orderID: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("orders.orderID", ondelete="CASCADE")
    )
    drink: Mapped[str] = mapped_column(String)
    milk: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    milk_volume: Mapped[float] = mapped_column(Float, nullable=True)
    shots: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    texture: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    options: Mapped[str] = mapped_column(String, nullable=True)
    customer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timeReceived: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    timeComplete: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    order: Mapped[Optional[Orders]] = relationship("Orders", back_populates="drinks")


class Database:
    def __init__(self, uri: str):
        self.uri = uri
        self.engine = create_async_engine(uri)
        self.sessions = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    def session(self) -> AsyncSession:
        return self.sessions()

    async def close(self) -> None:
        await self.engine.dispose()
