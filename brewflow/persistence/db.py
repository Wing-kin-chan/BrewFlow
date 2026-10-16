from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    event,
    inspect,
    insert,
    select,
    text,
)
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


class PosOrders(Base):
    __tablename__ = "pos_orders"
    __table_args__ = (
        CheckConstraint("currency = 'gbp'", name="ck_pos_orders_currency"),
        CheckConstraint(
            "status IN ('pending_payment', 'paid', 'queued')",
            name="ck_pos_orders_status",
        ),
        CheckConstraint("totalMinor >= 0", name="ck_pos_orders_total_minor"),
    )

    orderID: Mapped[str] = mapped_column(String, primary_key=True)
    customer: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String(3))
    totalMinor: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paidAt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    queuedAt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["PosOrderItems"]] = relationship(
        "PosOrderItems",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PosOrderItems.lineNumber",
    )
    attempts: Mapped[list["PaymentAttempts"]] = relationship(
        "PaymentAttempts", back_populates="order", cascade="all, delete-orphan"
    )


class PosOrderItems(Base):
    __tablename__ = "pos_order_items"
    __table_args__ = (
        CheckConstraint("lineNumber >= 0", name="ck_pos_order_items_line_number"),
        CheckConstraint(
            "unitAmountMinor >= 0", name="ck_pos_order_items_unit_amount_minor"
        ),
        UniqueConstraint("orderID", "lineNumber", name="uq_pos_order_items_line"),
    )

    identifier: Mapped[str] = mapped_column(String, primary_key=True)
    orderID: Mapped[str] = mapped_column(
        String, ForeignKey("pos_orders.orderID", ondelete="CASCADE")
    )
    lineNumber: Mapped[int] = mapped_column(Integer)
    catalogItemID: Mapped[str] = mapped_column(String)
    itemName: Mapped[str] = mapped_column(String)
    unitAmountMinor: Mapped[int] = mapped_column(Integer)
    drinkSnapshot: Mapped[str] = mapped_column(Text)

    order: Mapped[PosOrders] = relationship("PosOrders", back_populates="items")


class PaymentAttempts(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('creating', 'open', 'paid', 'expired', 'failed')",
            name="ck_payment_attempts_status",
        ),
        UniqueConstraint("idempotencyKey", name="uq_payment_attempts_idempotency_key"),
        UniqueConstraint("stripeSessionID", name="uq_payment_attempts_stripe_session_id"),
        UniqueConstraint(
            "stripePaymentIntentID", name="uq_payment_attempts_payment_intent_id"
        ),
    )

    attemptID: Mapped[str] = mapped_column(String, primary_key=True)
    orderID: Mapped[str] = mapped_column(
        String, ForeignKey("pos_orders.orderID", ondelete="CASCADE")
    )
    idempotencyKey: Mapped[str] = mapped_column(String)
    stripeSessionID: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stripePaymentIntentID: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    checkoutURL: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expiresAt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paidAt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    isDemo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )

    order: Mapped[PosOrders] = relationship("PosOrders", back_populates="attempts")


class CafeAccounts(Base):
    __tablename__ = "cafe_accounts"

    cafeID: Mapped[str] = mapped_column(String, primary_key=True)
    demoModeEnabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )


class Database:
    def __init__(self, uri: str):
        self.uri = uri
        self.engine = create_async_engine(uri)
        if self.engine.url.get_backend_name() == "sqlite":
            event.listen(self.engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        self.sessions = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            if self.engine.url.get_backend_name() == "sqlite":
                await connection.run_sync(_migrate_sqlite_schema)
            await connection.run_sync(Base.metadata.create_all)
            existing_cafe = await connection.execute(
                select(CafeAccounts.cafeID).where(CafeAccounts.cafeID == "local")
            )
            if existing_cafe.scalar_one_or_none() is None:
                await connection.execute(
                    insert(CafeAccounts).values(
                        cafeID="local", demoModeEnabled=False
                    )
                )

    def session(self) -> AsyncSession:
        return self.sessions()

    async def close(self) -> None:
        await self.engine.dispose()


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _migrate_sqlite_schema(connection) -> None:
    inspector = inspect(connection)
    if "payment_attempts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("payment_attempts")}
    if "isDemo" not in columns:
        connection.execute(
            text(
                'ALTER TABLE payment_attempts ADD COLUMN "isDemo" '
                "BOOLEAN NOT NULL DEFAULT 0"
            )
        )
