import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import time
from uuid import UUID

import pytest

from brewflow.domain.pos import PosOrderInput
from brewflow.domain.models import Order
from brewflow.payment_runtime import (
    DemoModeNotAllowedError,
    InvalidPosOrderError,
    PaymentProviderError,
    PaymentRuntime,
    PaymentVerificationError,
    PosConflictError,
)
from brewflow.queue_runtime import IntakeConflictError, QueueRuntime
from brewflow.settings import PaymentSettings, load_catalog_settings, load_queue_settings


ORDER_ID = "00000000-0000-4000-8000-000000000001"
DRINK_ID = "00000000-0000-4000-8000-000000000002"


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


class FakeSessions:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.create_calls: list[tuple[dict, dict]] = []
        self.sessions: dict[str, dict] = {}
        self.sessions_by_key: dict[str, dict] = {}
        self.fail_creates = 0

    def create(self, parameters: dict, options: dict):
        self.create_calls.append((parameters, options))
        if self.fail_creates:
            self.fail_creates -= 1
            raise RuntimeError("ambiguous provider failure")
        idempotency_key = options["idempotency_key"]
        if idempotency_key in self.sessions_by_key:
            return SimpleNamespace(**self.sessions_by_key[idempotency_key])
        session_id = f"cs_test_{len(self.create_calls)}"
        session = {
            "id": session_id,
            "url": f"https://checkout.stripe.com/test/{session_id}",
            "expires_at": int((self.clock() + timedelta(hours=1)).timestamp()),
            "status": "open",
            "mode": parameters["mode"],
            "payment_status": "unpaid",
            "currency": "gbp",
            "amount_total": sum(
                line["price_data"]["unit_amount"] * line["quantity"]
                for line in parameters["line_items"]
            ),
            "client_reference_id": parameters["client_reference_id"],
            "metadata": parameters["metadata"],
            "payment_intent": None,
        }
        self.sessions[session_id] = session
        self.sessions_by_key[idempotency_key] = session
        return SimpleNamespace(**session)

    def retrieve(self, session_id: str):
        return self.sessions[session_id]

    def pay(self, session_id: str, *, payment_intent: str = "pi_test_1") -> dict:
        session = self.sessions[session_id]
        session.update(
            status="complete", payment_status="paid", payment_intent=payment_intent
        )
        return session


class FakeStripeClient:
    def __init__(self, clock: Clock):
        self.sessions = FakeSessions(clock)
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=self.sessions)
        )


def payment_settings(
    *, timeout: float = 1.0, allow_demo_mode: bool = False
) -> PaymentSettings:
    return PaymentSettings(
        stripe_secret_key="sk_test_placeholder",
        stripe_webhook_secret="whsec_placeholder",
        checkout_return_base_url="http://127.0.0.1:8000",
        stripe_timeout_seconds=timeout,
        allow_demo_mode=allow_demo_mode,
    )


def pos_order(
    *,
    order_id: str = ORDER_ID,
    drink_id: str = DRINK_ID,
    customer: str | None = "Ada",
    catalog_item: str = "latte",
    milk: str = "Oat",
    texture: str | None = "Wet",
    options: list[str] | None = None,
) -> PosOrderInput:
    return PosOrderInput.model_validate(
        {
            "orderID": order_id,
            "customer": customer,
            "items": [
                {
                    "identifier": drink_id,
                    "catalogItemID": catalog_item,
                    "milk": milk,
                    "texture": texture,
                    "temperature": "Normal",
                    "options": options or [],
                }
            ],
        }
    )


async def make_runtime(tmp_path, *, clock=None, fake=None, allow_demo_mode=False):
    clock = clock or Clock()
    fake = fake or FakeStripeClient(clock)
    uri = f"sqlite+aiosqlite:///{tmp_path / 'payments.db'}"
    queue = await QueueRuntime.create(
        uri,
        load_queue_settings(),
        now=lambda: clock().replace(tzinfo=None),
    )
    payments = await PaymentRuntime.create(
        uri,
        queue,
        load_catalog_settings(),
        payment_settings(allow_demo_mode=allow_demo_mode),
        stripe_client=fake,
        now=clock,
    )
    return uri, queue, payments, fake, clock


async def close_runtime(queue, payments):
    await payments.close()
    await queue.close()


def paid_event(session: dict) -> dict:
    return {
        "id": "evt_test_paid",
        "type": "checkout.session.completed",
        "data": {"object": dict(session)},
    }


def test_catalog_has_approved_gbp_prices_and_explicit_milk_surcharges():
    catalog = load_catalog_settings()
    assert catalog.currency == "gbp"
    assert {item.name: item.price_minor for item in catalog.items} == {
        "Espresso": 280,
        "Cortado": 310,
        "Macchiato": 300,
        "Flat White": 320,
        "Cappuccino": 340,
        "Latte": 340,
        "Small Latte": 320,
        "Small Cappuccino": 320,
        "Long Black": 300,
        "Short Black": 290,
        "Mocha": 360,
        "Chai Latte": 350,
    }
    assert catalog.milk_surcharges_minor == {
        "No Milk": 0,
        "Whole": 0,
        "Semi-skimmed": 0,
        "Oat": 60,
        "Soy": 60,
    }


@pytest.mark.asyncio
async def test_checkout_is_server_priced_persisted_first_and_idempotent(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    submitted = pos_order(customer="   ", options=["Decaf"])
    try:
        first, second = await asyncio.gather(
            payments.create_checkout(submitted), payments.create_checkout(submitted)
        )
        assert first == second
        assert first.totalMinor == 400
        assert first.items[0].unitAmountMinor == 400
        assert first.items[0].name == "Latte"
        assert len(fake.sessions.create_calls) == 1
        parameters, options = fake.sessions.create_calls[0]
        assert parameters["payment_method_types"] == ["card"]
        assert parameters["line_items"][0]["price_data"] == {
            "currency": "gbp",
            "unit_amount": 400,
            "product_data": {
                "name": "Latte",
                "description": "Oat · Wet · Normal · Decaf",
            },
        }
        assert options["idempotency_key"].startswith("checkout-session:")
        stored = await payments.store.get_order(ORDER_ID)
        assert stored is not None
        assert stored.order.customer == "Customer"
        assert stored.status == "pending_payment"
        assert await queue.store.get_order(ORDER_ID) is None
        with pytest.raises(IntakeConflictError, match="reserved"):
            await queue.intake(
                Order(
                    orderID=stored.order.orderID,
                    customer=stored.order.customer,
                    drinks=[item.drink for item in stored.order.items],
                )
            )

        with pytest.raises(PosConflictError):
            await payments.create_checkout(pos_order(customer="Grace"))

        with pytest.raises(PosConflictError, match="drink identifier"):
            await payments.create_checkout(
                pos_order(order_id="00000000-0000-4000-8000-000000000099")
            )
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_stripe_bound_and_paid_order_snapshots_cannot_be_overwritten(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    original = pos_order(customer="Ada", options=["Decaf"])
    changed = pos_order(
        drink_id="00000000-0000-4000-8000-000000000003",
        customer="Grace",
    )
    try:
        checkout = await payments.create_checkout(original)
        before_payment = await payments.store.get_order(ORDER_ID)

        with pytest.raises(PosConflictError, match="different content"):
            await payments.create_checkout(changed)
        assert await payments.store.get_order(ORDER_ID) == before_payment
        assert len(fake.sessions.create_calls) == 1

        session = fake.sessions.pay(checkout.stripeSessionID)
        await payments.handle_webhook_event(paid_event(session))
        with pytest.raises(PosConflictError, match="different content"):
            await payments.create_checkout(changed)

        stored = await payments.store.get_order(ORDER_ID)
        queued = await queue.store.get_order(ORDER_ID)
        assert stored is not None and stored.status == "queued"
        assert stored.order.customer == "Ada"
        assert stored.order.items[0].identifier == DRINK_ID
        assert queued is not None and queued.drinks[0].identifier == DRINK_ID
        assert len(fake.sessions.create_calls) == 1
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_invalid_catalog_customizations_never_create_payment(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    try:
        with pytest.raises(InvalidPosOrderError):
            await payments.create_checkout(pos_order(catalog_item="unknown"))
        with pytest.raises(InvalidPosOrderError):
            await payments.create_checkout(pos_order(milk="Mystery"))
        with pytest.raises(InvalidPosOrderError):
            await payments.create_checkout(pos_order(options=["Unknown Option"]))
        with pytest.raises(InvalidPosOrderError):
            await payments.create_checkout(
                pos_order(options=["Single Shot", "Extra Shot"])
            )
        with pytest.raises(InvalidPosOrderError):
            await payments.create_checkout(
                pos_order(catalog_item="espresso", milk="Whole", texture="Wet")
            )
        assert not fake.sessions.create_calls
        assert await payments.store.get_order(ORDER_ID) is None
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_ambiguous_provider_failure_reuses_key_then_fails_closed_after_23_hours(
    tmp_path,
):
    clock = Clock()
    fake = FakeStripeClient(clock)
    fake.sessions.fail_creates = 2
    _, queue, payments, _, _ = await make_runtime(tmp_path, clock=clock, fake=fake)
    try:
        with pytest.raises(PaymentProviderError):
            await payments.create_checkout(pos_order())
        first_key = fake.sessions.create_calls[0][1]["idempotency_key"]
        with pytest.raises(PaymentProviderError):
            await payments.create_checkout(pos_order())
        assert fake.sessions.create_calls[1][1]["idempotency_key"] == first_key

        clock.value += timedelta(hours=23)
        with pytest.raises(PaymentProviderError, match="manual reconciliation"):
            await payments.create_checkout(pos_order())
        assert len(fake.sessions.create_calls) == 2
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_provider_timeout_is_sanitized_and_leaves_durable_creating_attempt(
    tmp_path, monkeypatch
):
    clock = Clock()
    fake = FakeStripeClient(clock)

    def slow_create(parameters, options):
        time.sleep(0.2)
        return SimpleNamespace(
            id="cs_late",
            url="https://checkout.stripe.com/test/cs_late",
            expires_at=int((clock() + timedelta(hours=1)).timestamp()),
        )

    monkeypatch.setattr(fake.sessions, "create", slow_create)
    uri = f"sqlite+aiosqlite:///{tmp_path / 'timeout.db'}"
    queue = await QueueRuntime.create(
        uri, load_queue_settings(), now=lambda: clock().replace(tzinfo=None)
    )
    payments = await PaymentRuntime.create(
        uri,
        queue,
        load_catalog_settings(),
        payment_settings(timeout=0.01),
        stripe_client=fake,
        now=clock,
    )
    try:
        started = time.monotonic()
        with pytest.raises(PaymentProviderError, match="timed out"):
            await payments.create_checkout(pos_order())
        assert time.monotonic() - started < 0.15
        stored = await payments.store.get_order(ORDER_ID)
        assert stored is not None
        assert stored.latest_attempt.status == "creating"
        assert stored.latest_attempt.stripe_session_id is None
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_session_is_recovered_with_same_idempotency_key_after_local_write_failure(
    tmp_path, monkeypatch
):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    original = payments.store.set_attempt_open
    calls = 0

    async def fail_first(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database write failed")
        return await original(*args, **kwargs)

    monkeypatch.setattr(payments.store, "set_attempt_open", fail_first)
    try:
        with pytest.raises(RuntimeError, match="database write failed"):
            await payments.create_checkout(pos_order())
        recovered = await payments.create_checkout(pos_order())
        assert recovered.stripeSessionID == "cs_test_1"
        assert len(fake.sessions.sessions) == 1
        assert len(fake.sessions.create_calls) == 2
        assert (
            fake.sessions.create_calls[0][1]["idempotency_key"]
            == fake.sessions.create_calls[1][1]["idempotency_key"]
        )
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_pending_persistence_failure_never_contacts_stripe(
    tmp_path, monkeypatch
):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)

    async def fail(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(payments.store, "add_pending", fail)
    try:
        with pytest.raises(RuntimeError, match="database unavailable"):
            await payments.create_checkout(pos_order())
        assert not fake.sessions.create_calls
        assert await payments.store.get_order(ORDER_ID) is None
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_verified_paid_webhook_is_exactly_once_and_uses_server_queue_timestamp(
    tmp_path,
):
    _, queue, payments, fake, clock = await make_runtime(tmp_path)
    try:
        checkout = await payments.create_checkout(pos_order(options=["Extra Shot"]))
        session = fake.sessions.pay(checkout.stripeSessionID)
        await asyncio.gather(
            payments.handle_webhook_event(paid_event(session)),
            payments.handle_webhook_event(paid_event(session)),
        )

        stored = await payments.store.get_order(ORDER_ID)
        queued = await queue.store.get_order(ORDER_ID)
        assert stored is not None and stored.status == "queued"
        assert queued is not None
        assert queued.timeReceived == clock().replace(tzinfo=None).time()
        assert queued.drinks[0].identifier == DRINK_ID
        assert queued.drinks[0].shots == 3
        assert (await queue.queue_snapshot()).totalDrinks == 1
        assert len(queue.queue.history) == 1
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("amount_total", 1),
        ("currency", "usd"),
        ("client_reference_id", "wrong"),
        ("mode", "setup"),
        ("metadata", {"order_id": ORDER_ID, "attempt_id": "wrong"}),
    ),
)
async def test_reconciliation_mismatch_never_marks_paid_or_queues(
    tmp_path, field, value
):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    try:
        checkout = await payments.create_checkout(pos_order())
        session = fake.sessions.pay(checkout.stripeSessionID)
        session[field] = value
        with pytest.raises(PaymentVerificationError):
            await payments.handle_webhook_event(paid_event(session))
        stored = await payments.store.get_order(ORDER_ID)
        assert stored is not None and stored.status == "pending_payment"
        assert await queue.store.get_order(ORDER_ID) is None
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_unpaid_completed_event_is_acknowledged_without_queueing(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    try:
        checkout = await payments.create_checkout(pos_order())
        session = fake.sessions.sessions[checkout.stripeSessionID]
        session["status"] = "complete"
        await payments.handle_webhook_event(paid_event(session))
        assert await queue.store.get_order(ORDER_ID) is None
        assert (await payments.store.get_order(ORDER_ID)).status == "pending_payment"
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_paid_unqueued_order_recovers_after_post_queue_marker_failure(
    tmp_path, monkeypatch
):
    uri, queue, payments, fake, clock = await make_runtime(tmp_path)
    checkout = await payments.create_checkout(pos_order())
    session = fake.sessions.pay(checkout.stripeSessionID)
    original_mark_queued = payments.store.mark_queued

    async def fail_once(*args, **kwargs):
        raise RuntimeError("marker write failed")

    monkeypatch.setattr(payments.store, "mark_queued", fail_once)
    with pytest.raises(RuntimeError, match="marker write failed"):
        await payments.handle_webhook_event(paid_event(session))
    assert await queue.store.get_order(ORDER_ID) is not None
    assert (await payments.store.get_order(ORDER_ID)).status == "paid"
    await queue.complete({DRINK_ID})
    assert (await queue.queue_snapshot()).totalDrinks == 0
    monkeypatch.setattr(payments.store, "mark_queued", original_mark_queued)
    await payments.close()

    recovered = await PaymentRuntime.create(
        uri,
        queue,
        load_catalog_settings(),
        payment_settings(),
        stripe_client=fake,
        now=clock,
    )
    try:
        assert (await recovered.store.get_order(ORDER_ID)).status == "queued"
        assert (await queue.queue_snapshot()).totalDrinks == 0
        assert len(queue.queue.history) == 1
    finally:
        await recovered.close()
        await queue.close()


@pytest.mark.asyncio
async def test_receipt_poll_recovers_paid_order_after_queue_failure(tmp_path, monkeypatch):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    checkout = await payments.create_checkout(pos_order())
    session = fake.sessions.pay(checkout.stripeSessionID)
    original_intake = queue.intake

    async def fail_once(_order, **_kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(queue, "intake", fail_once)
    with pytest.raises(RuntimeError, match="queue unavailable"):
        await payments.handle_webhook_event(paid_event(session))
    assert (await payments.store.get_order(ORDER_ID)).status == "paid"
    assert await queue.store.get_order(ORDER_ID) is None

    monkeypatch.setattr(queue, "intake", original_intake)
    try:
        receipt = await payments.receipt(checkout.stripeSessionID)
        assert receipt is not None and receipt.status == "queued"
        assert await queue.store.get_order(ORDER_ID) is not None
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_replacement_session_requires_authoritative_expiry(tmp_path):
    clock = Clock()
    _, queue, payments, fake, _ = await make_runtime(tmp_path, clock=clock)
    try:
        first = await payments.create_checkout(pos_order())
        clock.value += timedelta(hours=2)
        still_first = await payments.create_checkout(pos_order())
        assert still_first.stripeSessionID == first.stripeSessionID
        assert len(fake.sessions.create_calls) == 1

        fake.sessions.sessions[first.stripeSessionID]["status"] = "expired"
        replacement = await payments.create_checkout(pos_order())
        assert replacement.stripeSessionID != first.stripeSessionID
        assert len(fake.sessions.create_calls) == 2
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_signed_expiry_event_allows_one_replacement_session(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(tmp_path)
    try:
        first = await payments.create_checkout(pos_order())
        expired = fake.sessions.sessions[first.stripeSessionID]
        expired["status"] = "expired"
        await payments.handle_webhook_event(
            {"type": "checkout.session.expired", "data": {"object": expired}}
        )
        replacement = await payments.create_checkout(pos_order())
        assert replacement.stripeSessionID != first.stripeSessionID
        assert len(fake.sessions.create_calls) == 2
    finally:
        await close_runtime(queue, payments)


def test_stage_2_inputs_require_canonical_uuid_and_reject_unknown_fields():
    with pytest.raises(ValueError):
        pos_order(order_id="not-a-uuid")
    payload = pos_order().model_dump(mode="json")
    payload["trustedPrice"] = 1
    with pytest.raises(ValueError):
        PosOrderInput.model_validate(payload)
    forged = pos_order().model_dump(mode="json")
    forged["isDemo"] = True
    with pytest.raises(ValueError):
        PosOrderInput.model_validate(forged)
    too_many = pos_order().model_dump(mode="json")
    too_many["items"] = [
        {
            **too_many["items"][0],
            "identifier": f"00000000-0000-4000-8000-{number:012d}",
        }
        for number in range(51)
    ]
    with pytest.raises(ValueError):
        PosOrderInput.model_validate(too_many)
    assert isinstance(pos_order().orderID, UUID)


@pytest.mark.asyncio
async def test_demo_gate_controls_server_derived_checkout_without_stripe_calls(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(
        tmp_path, allow_demo_mode=False
    )
    try:
        with pytest.raises(DemoModeNotAllowedError):
            await payments.set_demo_mode(True)
        assert (await payments.configuration()).demoModeEnabled is False
    finally:
        await close_runtime(queue, payments)

    enabled_path = tmp_path / "enabled"
    enabled_path.mkdir()
    _, queue, payments, fake, _ = await make_runtime(
        enabled_path, allow_demo_mode=True
    )
    try:
        configuration = await payments.set_demo_mode(True)
        assert configuration.demoModeEnabled is True
        checkout = await payments.create_checkout(pos_order())
        assert checkout.isDemo is True
        assert checkout.stripeSessionID is None
        assert checkout.checkoutURL is None
        assert not fake.sessions.create_calls
        stored = await payments.store.get_order(ORDER_ID)
        assert stored is not None and stored.latest_attempt.is_demo is True

        await payments.set_demo_mode(False)
        frozen = await payments.create_checkout(pos_order())
        assert frozen.isDemo is True and frozen.demoBlocked is True
        assert not fake.sessions.create_calls
        with pytest.raises(DemoModeNotAllowedError):
            await payments.submit_demo_payment(ORDER_ID)
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_demo_submit_is_concurrent_idempotent_and_reaches_history(tmp_path):
    _, queue, payments, fake, _ = await make_runtime(
        tmp_path, allow_demo_mode=True
    )
    try:
        await payments.set_demo_mode(True)
        await payments.create_checkout(pos_order())
        first, second = await asyncio.gather(
            payments.submit_demo_payment(ORDER_ID),
            payments.submit_demo_payment(ORDER_ID),
        )
        assert first.status == second.status == "queued"
        assert not fake.sessions.create_calls
        assert (await queue.queue_snapshot()).totalDrinks == 1
        assert len(queue.queue.history) == 1

        await queue.complete({DRINK_ID})
        history = await queue.history_snapshot()
        assert history.totalDrinks == 1
        assert history.orders[0].orderID == ORDER_ID
    finally:
        await close_runtime(queue, payments)


@pytest.mark.asyncio
async def test_paid_demo_recovery_fails_closed_until_gate_is_enabled(tmp_path, monkeypatch):
    uri, queue, payments, fake, clock = await make_runtime(
        tmp_path, allow_demo_mode=True
    )
    await payments.set_demo_mode(True)
    await payments.create_checkout(pos_order())
    original_intake = queue.intake

    async def fail_intake(*_args, **_kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(queue, "intake", fail_intake)
    with pytest.raises(RuntimeError, match="queue unavailable"):
        await payments.submit_demo_payment(ORDER_ID)
    assert (await payments.store.get_order(ORDER_ID)).status == "paid"
    await payments.close()
    monkeypatch.setattr(queue, "intake", original_intake)

    blocked = await PaymentRuntime.create(
        uri,
        queue,
        load_catalog_settings(),
        payment_settings(allow_demo_mode=False),
        stripe_client=fake,
        now=clock,
    )
    try:
        assert await queue.store.get_order(ORDER_ID) is None
        receipt = await blocked.demo_receipt(ORDER_ID)
        assert receipt is not None and receipt.demoBlocked is True
        assert receipt.status == "paid"
    finally:
        await blocked.close()

    recovered = await PaymentRuntime.create(
        uri,
        queue,
        load_catalog_settings(),
        payment_settings(allow_demo_mode=True),
        stripe_client=fake,
        now=clock,
    )
    try:
        assert (await recovered.store.get_order(ORDER_ID)).status == "queued"
        assert (await queue.queue_snapshot()).totalDrinks == 1
        assert not fake.sessions.create_calls
    finally:
        await recovered.close()
        await queue.close()


@pytest.mark.asyncio
async def test_disable_failure_leaves_demo_enabled_and_real_webhook_still_works(tmp_path, monkeypatch):
    _, queue, payments, fake, _ = await make_runtime(
        tmp_path, allow_demo_mode=True
    )
    try:
        real = await payments.create_checkout(pos_order())
        await payments.set_demo_mode(True)
        session = fake.sessions.pay(real.stripeSessionID)
        await payments.handle_webhook_event(paid_event(session))
        assert (await payments.store.get_order(ORDER_ID)).status == "queued"

        second = pos_order(
            order_id="00000000-0000-4000-8000-000000000011",
            drink_id="00000000-0000-4000-8000-000000000012",
        )
        await payments.create_checkout(second)
        stored = await payments.store.get_order(str(second.orderID))
        await payments.store.mark_demo_paid(
            stored.latest_attempt.attempt_id, paid_at=payments._now()
        )
        original_intake = queue.intake

        async def fail_intake(*_args, **_kwargs):
            raise RuntimeError("queue unavailable")

        monkeypatch.setattr(queue, "intake", fail_intake)
        with pytest.raises(RuntimeError, match="queue unavailable"):
            await payments.set_demo_mode(False)
        configuration = await payments.configuration()
        assert configuration.demoModeEnabled is True
        assert configuration.demoModePersisted is True

        monkeypatch.setattr(queue, "intake", original_intake)
        disabled = await payments.set_demo_mode(False)
        assert disabled.demoModeEnabled is False
    finally:
        await close_runtime(queue, payments)
