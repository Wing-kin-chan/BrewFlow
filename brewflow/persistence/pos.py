from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from brewflow.domain.models import Drink
from brewflow.domain.pos import CanonicalPosItem, CanonicalPosOrder
from brewflow.persistence.db import (
    CafeAccounts,
    Database,
    PaymentAttempts,
    PosOrderItems,
    PosOrders,
)


@dataclass(frozen=True)
class StoredPaymentAttempt:
    attempt_id: str
    order_id: str
    idempotency_key: str
    stripe_session_id: str | None
    stripe_payment_intent_id: str | None
    checkout_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    paid_at: datetime | None
    is_demo: bool


@dataclass(frozen=True)
class StoredPosOrder:
    order: CanonicalPosOrder
    status: str
    created_at: datetime
    paid_at: datetime | None
    queued_at: datetime | None
    attempts: tuple[StoredPaymentAttempt, ...]

    @property
    def latest_attempt(self) -> StoredPaymentAttempt:
        return max(
            self.attempts,
            key=lambda attempt: (
                attempt.status not in {"expired", "failed"},
                attempt.created_at,
                attempt.attempt_id,
            ),
        )


def _attempt_from_record(record: PaymentAttempts) -> StoredPaymentAttempt:
    return StoredPaymentAttempt(
        attempt_id=record.attemptID,
        order_id=record.orderID,
        idempotency_key=record.idempotencyKey,
        stripe_session_id=record.stripeSessionID,
        stripe_payment_intent_id=record.stripePaymentIntentID,
        checkout_url=record.checkoutURL,
        status=record.status,
        created_at=record.createdAt,
        updated_at=record.updatedAt,
        expires_at=record.expiresAt,
        paid_at=record.paidAt,
        is_demo=record.isDemo,
    )


def _order_from_record(record: PosOrders) -> StoredPosOrder:
    items = [
        CanonicalPosItem(
            identifier=item.identifier,
            catalogItemID=item.catalogItemID,
            name=item.itemName,
            unitAmountMinor=item.unitAmountMinor,
            drink=Drink.model_validate_json(item.drinkSnapshot),
        )
        for item in record.items
    ]
    return StoredPosOrder(
        order=CanonicalPosOrder(
            orderID=record.orderID,
            customer=record.customer,
            currency=record.currency,
            totalMinor=record.totalMinor,
            items=items,
        ),
        status=record.status,
        created_at=record.createdAt,
        paid_at=record.paidAt,
        queued_at=record.queuedAt,
        attempts=tuple(_attempt_from_record(attempt) for attempt in record.attempts),
    )


class PosStore:
    def __init__(self, database: Database, session: AsyncSession):
        self.database = database
        self.session = session

    @classmethod
    async def create(cls, uri: str) -> "PosStore":
        database = Database(uri)
        await database.initialize()
        return cls(database, database.session())

    async def close(self) -> None:
        await self.session.close()
        await self.database.close()

    def _order_query(self):
        return select(PosOrders).options(
            selectinload(PosOrders.items), selectinload(PosOrders.attempts)
        )

    async def get_order(self, order_id: str) -> StoredPosOrder | None:
        result = await self.session.execute(
            self._order_query()
            .where(PosOrders.orderID == order_id)
            .execution_options(populate_existing=True)
        )
        record = result.scalar_one_or_none()
        return _order_from_record(record) if record else None

    async def get_order_by_session(self, session_id: str) -> StoredPosOrder | None:
        result = await self.session.execute(
            self._order_query()
            .join(PaymentAttempts)
            .where(PaymentAttempts.stripeSessionID == session_id)
            .execution_options(populate_existing=True)
        )
        record = result.scalar_one_or_none()
        return _order_from_record(record) if record else None

    async def item_identifiers_exist(self, identifiers: set[str]) -> bool:
        if not identifiers:
            return False
        result = await self.session.execute(
            select(PosOrderItems.identifier)
            .where(PosOrderItems.identifier.in_(identifiers))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add_pending(
        self,
        order: CanonicalPosOrder,
        *,
        attempt_id: str,
        idempotency_key: str,
        created_at: datetime,
        is_demo: bool = False,
    ) -> None:
        try:
            record = PosOrders(
                orderID=order.orderID,
                customer=order.customer,
                currency=order.currency,
                totalMinor=order.totalMinor,
                status="pending_payment",
                createdAt=created_at,
            )
            record.items = [
                PosOrderItems(
                    identifier=item.identifier,
                    orderID=order.orderID,
                    lineNumber=line_number,
                    catalogItemID=item.catalogItemID,
                    itemName=item.name,
                    unitAmountMinor=item.unitAmountMinor,
                    drinkSnapshot=item.drink.model_dump_json(),
                )
                for line_number, item in enumerate(order.items)
            ]
            record.attempts = [
                PaymentAttempts(
                    attemptID=attempt_id,
                    orderID=order.orderID,
                    idempotencyKey=idempotency_key,
                    status="open" if is_demo else "creating",
                    createdAt=created_at,
                    updatedAt=created_at,
                    isDemo=is_demo,
                )
            ]
            self.session.add(record)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def add_attempt(
        self,
        order_id: str,
        *,
        attempt_id: str,
        idempotency_key: str,
        created_at: datetime,
        is_demo: bool = False,
    ) -> None:
        try:
            self.session.add(
                PaymentAttempts(
                    attemptID=attempt_id,
                    orderID=order_id,
                    idempotencyKey=idempotency_key,
                    status="creating",
                    createdAt=created_at,
                    updatedAt=created_at,
                    isDemo=is_demo,
                )
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def set_attempt_open(
        self,
        attempt_id: str,
        *,
        session_id: str,
        checkout_url: str,
        expires_at: datetime,
        updated_at: datetime,
    ) -> None:
        attempt = await self.session.get(PaymentAttempts, attempt_id)
        if attempt is None:
            raise LookupError("Payment attempt not found")
        try:
            attempt.stripeSessionID = session_id
            attempt.checkoutURL = checkout_url
            attempt.expiresAt = expires_at
            attempt.status = "open"
            attempt.updatedAt = updated_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def mark_attempt_expired(
        self, session_id: str, *, updated_at: datetime
    ) -> None:
        result = await self.session.execute(
            select(PaymentAttempts).where(
                PaymentAttempts.stripeSessionID == session_id
            )
        )
        attempt = result.scalar_one_or_none()
        if attempt is None or attempt.status in {"paid", "expired"}:
            return
        try:
            attempt.status = "expired"
            attempt.updatedAt = updated_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def mark_paid(
        self,
        session_id: str,
        *,
        payment_intent_id: str,
        paid_at: datetime,
    ) -> StoredPosOrder:
        result = await self.session.execute(
            select(PaymentAttempts)
            .where(PaymentAttempts.stripeSessionID == session_id)
            .options(selectinload(PaymentAttempts.order))
        )
        attempt = result.scalar_one_or_none()
        if attempt is None or attempt.order is None:
            raise LookupError("Payment attempt not found")
        try:
            if attempt.order.status == "pending_payment":
                attempt.order.status = "paid"
                attempt.order.paidAt = paid_at
            attempt.status = "paid"
            attempt.stripePaymentIntentID = payment_intent_id
            attempt.paidAt = paid_at
            attempt.updatedAt = paid_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        stored = await self.get_order(attempt.orderID)
        if stored is None:
            raise LookupError("Paid order not found")
        return stored

    async def mark_demo_paid(
        self, attempt_id: str, *, paid_at: datetime
    ) -> StoredPosOrder:
        attempt = await self.session.get(PaymentAttempts, attempt_id)
        if attempt is None or not attempt.isDemo:
            raise LookupError("Demo payment attempt not found")
        order = await self.session.get(PosOrders, attempt.orderID)
        if order is None:
            raise LookupError("POS order not found")
        try:
            if order.status == "pending_payment":
                order.status = "paid"
                order.paidAt = paid_at
            attempt.status = "paid"
            attempt.paidAt = paid_at
            attempt.updatedAt = paid_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        stored = await self.get_order(attempt.orderID)
        if stored is None:
            raise LookupError("Paid order not found")
        return stored

    async def mark_queued(self, order_id: str, *, queued_at: datetime) -> None:
        record = await self.session.get(PosOrders, order_id)
        if record is None:
            raise LookupError("POS order not found")
        if record.status == "queued":
            return
        if record.status != "paid":
            raise ValueError("Only paid orders can be queued")
        try:
            record.status = "queued"
            record.queuedAt = queued_at
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def paid_unqueued(self) -> list[StoredPosOrder]:
        result = await self.session.execute(
            self._order_query()
            .where(PosOrders.status == "paid")
            .execution_options(populate_existing=True)
        )
        return [_order_from_record(record) for record in result.scalars().all()]

    async def demo_mode_enabled(self) -> bool:
        record = await self.session.get(CafeAccounts, "local")
        if record is None:
            raise RuntimeError("Local cafe configuration is missing")
        return record.demoModeEnabled

    async def set_demo_mode_enabled(self, enabled: bool) -> None:
        record = await self.session.get(CafeAccounts, "local")
        if record is None:
            raise RuntimeError("Local cafe configuration is missing")
        try:
            record.demoModeEnabled = enabled
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
