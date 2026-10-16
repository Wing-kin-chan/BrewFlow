import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import stripe
from anyio import to_thread

from brewflow.domain.models import Drink, Order
from brewflow.domain.pos import (
    CanonicalPosItem,
    CanonicalPosOrder,
    CatalogItemResponse,
    CatalogResponse,
    CheckoutResponse,
    DemoModeResponse,
    PosOrderInput,
    ReceiptResponse,
)
from brewflow.persistence.pos import PosStore, StoredPaymentAttempt, StoredPosOrder
from brewflow.queue_runtime import QueueRuntime
from brewflow.settings import CatalogSettings, PaymentSettings


CREATING_ATTEMPT_LIFETIME = timedelta(hours=23)


class PosConflictError(Exception):
    pass


class InvalidPosOrderError(Exception):
    pass


class PaymentNotConfiguredError(Exception):
    pass


class PaymentProviderError(Exception):
    pass


class PaymentVerificationError(Exception):
    pass


class DemoModeNotAllowedError(Exception):
    pass


class DemoPaymentError(Exception):
    pass


def _value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class PaymentRuntime:
    def __init__(
        self,
        store: PosStore,
        queue_runtime: QueueRuntime,
        catalog: CatalogSettings,
        settings: PaymentSettings,
        *,
        stripe_client: Any = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.store = store
        self.queue_runtime = queue_runtime
        self.catalog = catalog
        self.settings = settings
        if catalog.currency != "gbp":
            raise ValueError("Stage 2 payments require a GBP catalog")
        if settings.stripe_timeout_seconds <= 0:
            raise ValueError("Stripe timeout must be positive")
        self.stripe_client = stripe_client
        if self.stripe_client is None and settings.stripe_secret_key:
            self.stripe_client = stripe.StripeClient(
                settings.stripe_secret_key,
                http_client=stripe.RequestsClient(
                    timeout=settings.stripe_timeout_seconds
                ),
                max_network_retries=0,
            )
        self.lock = asyncio.Lock()
        self._now = now
        self._catalog_by_id = {item.identifier: item for item in catalog.items}

    @classmethod
    async def create(
        cls,
        database_uri: str,
        queue_runtime: QueueRuntime,
        catalog: CatalogSettings,
        settings: PaymentSettings,
        *,
        stripe_client: Any = None,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> "PaymentRuntime":
        store = await PosStore.create(database_uri)
        try:
            runtime = cls(
                store,
                queue_runtime,
                catalog,
                settings,
                stripe_client=stripe_client,
                now=now,
            )
            await runtime.recover_paid_orders()
            return runtime
        except Exception:
            await store.close()
            raise

    async def close(self) -> None:
        await self.store.close()

    def catalog_response(self) -> CatalogResponse:
        return CatalogResponse(
            currency="gbp",
            items=[
                CatalogItemResponse(
                    id=item.identifier,
                    name=item.name,
                    priceMinor=item.price_minor,
                    milkVolume=item.milk_volume,
                    shots=item.shots,
                    texture=item.texture,
                )
                for item in self.catalog.items
            ],
            milks=list(self.catalog.milks),
            textures=list(self.catalog.textures),
            options=list(self.catalog.options),
            milkSurchargesMinor=dict(self.catalog.milk_surcharges_minor),
        )

    def _canonicalize(self, submitted: PosOrderInput) -> CanonicalPosOrder:
        order_id = str(submitted.orderID)
        customer = submitted.customer or "Customer"
        seen: set[str] = set()
        items: list[CanonicalPosItem] = []
        valid_options = set(self.catalog.options)

        for submitted_item in submitted.items:
            identifier = str(submitted_item.identifier)
            if identifier in seen:
                raise InvalidPosOrderError("Drink identifiers must be unique")
            seen.add(identifier)
            catalog_item = self._catalog_by_id.get(submitted_item.catalogItemID)
            if catalog_item is None:
                raise InvalidPosOrderError("Unknown catalog item")

            if len(set(submitted_item.options)) != len(submitted_item.options):
                raise InvalidPosOrderError("Drink options must be unique")
            unknown_options = set(submitted_item.options) - valid_options
            if unknown_options:
                raise InvalidPosOrderError("Unknown drink option")
            options = [
                option
                for option in self.catalog.options
                if option in submitted_item.options
            ]

            shot_options = {
                option
                for option in options
                if option in {"Single Shot", "Extra Shot", "Extra Shot x2"}
            }
            if len(shot_options) > 1:
                raise InvalidPosOrderError("Choose at most one shot option")
            shots = catalog_item.shots
            if "Single Shot" in shot_options:
                shots = 1
            elif "Extra Shot" in shot_options:
                shots += 1
            elif "Extra Shot x2" in shot_options:
                shots += 2

            temperature_options = {
                option for option in options if option in {"Warm", "Extra Hot"}
            }
            if len(temperature_options) > 1:
                raise InvalidPosOrderError("Choose at most one temperature option")
            if temperature_options and submitted_item.temperature not in temperature_options:
                raise InvalidPosOrderError(
                    "Temperature option must match the selected temperature"
                )

            if catalog_item.milk_volume == 0:
                if submitted_item.milk != "No Milk" or submitted_item.texture is not None:
                    raise InvalidPosOrderError(
                        "This catalog item does not accept milk customizations"
                    )
            else:
                if submitted_item.milk not in self.catalog.milks:
                    raise InvalidPosOrderError("Unknown milk")
                if submitted_item.texture not in self.catalog.textures:
                    raise InvalidPosOrderError("Unknown milk texture")

            surcharge = self.catalog.milk_surcharges_minor.get(submitted_item.milk)
            if surcharge is None or surcharge < 0:
                raise InvalidPosOrderError("Milk pricing is not configured")
            unit_amount = catalog_item.price_minor + surcharge
            drink = Drink(
                identifier=identifier,
                orderID=order_id,
                customer=customer,
                drink=catalog_item.name,
                milk=submitted_item.milk,
                milk_volume=catalog_item.milk_volume,
                shots=shots,
                temperature=submitted_item.temperature,
                texture=submitted_item.texture,
                options=options,
            )
            items.append(
                CanonicalPosItem(
                    identifier=identifier,
                    catalogItemID=catalog_item.identifier,
                    name=catalog_item.name,
                    unitAmountMinor=unit_amount,
                    drink=drink,
                )
            )

        return CanonicalPosOrder(
            orderID=order_id,
            customer=customer,
            currency="gbp",
            totalMinor=sum(item.unitAmountMinor for item in items),
            items=items,
        )

    def _same_order(
        self, stored: CanonicalPosOrder, submitted: CanonicalPosOrder
    ) -> bool:
        return stored.model_dump(mode="json") == submitted.model_dump(mode="json")

    async def _stripe_call(self, callback: Callable[[], Any]) -> Any:
        try:
            return await asyncio.wait_for(
                to_thread.run_sync(callback, abandon_on_cancel=True),
                timeout=self.settings.stripe_timeout_seconds,
            )
        except TimeoutError as error:
            raise PaymentProviderError("Payment provider timed out") from error
        except stripe.StripeError as error:
            raise PaymentProviderError("Payment provider request failed") from error
        except PaymentProviderError:
            raise
        except Exception as error:
            raise PaymentProviderError("Payment provider request failed") from error

    def _session_create_parameters(
        self, order: CanonicalPosOrder, attempt_id: str
    ) -> dict[str, Any]:
        base_url = self.settings.checkout_return_base_url
        return {
            "mode": "payment",
            "payment_method_types": ["card"],
            "client_reference_id": order.orderID,
            "metadata": {"order_id": order.orderID, "attempt_id": attempt_id},
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": order.currency,
                        "unit_amount": item.unitAmountMinor,
                        "product_data": {
                            "name": item.name,
                            "description": " · ".join(
                                filter(
                                    None,
                                    [
                                        item.drink.milk,
                                        item.drink.texture,
                                        item.drink.temperature,
                                        ", ".join(item.drink.options),
                                    ],
                                )
                            ),
                        },
                    },
                }
                for item in order.items
            ],
            "success_url": (
                f"{base_url}/api/receipt?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            "cancel_url": f"{base_url}/api/pos",
        }

    async def _create_stripe_session(
        self, order: CanonicalPosOrder, attempt: StoredPaymentAttempt
    ) -> StoredPosOrder:
        if self.stripe_client is None:
            raise PaymentNotConfiguredError("Stripe is not configured")
        created = await self._stripe_call(
            lambda: self.stripe_client.v1.checkout.sessions.create(
                self._session_create_parameters(order, attempt.attempt_id),
                options={"idempotency_key": attempt.idempotency_key},
            )
        )
        session_id = _value(created, "id")
        checkout_url = _value(created, "url")
        expires_at = _value(created, "expires_at")
        parsed_checkout_url = urlparse(checkout_url or "")
        try:
            valid_checkout_url = (
                parsed_checkout_url.scheme == "https"
                and parsed_checkout_url.hostname == "checkout.stripe.com"
                and parsed_checkout_url.username is None
                and parsed_checkout_url.password is None
                and parsed_checkout_url.port is None
            )
        except ValueError:
            valid_checkout_url = False
        if (
            not isinstance(session_id, str)
            or not session_id
            or not valid_checkout_url
            or type(expires_at) is not int
        ):
            raise PaymentProviderError("Payment provider returned an invalid session")
        now = self._now()
        await self.store.set_attempt_open(
            attempt.attempt_id,
            session_id=session_id,
            checkout_url=checkout_url,
            expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
            updated_at=now,
        )
        stored = await self.store.get_order(order.orderID)
        if stored is None:
            raise RuntimeError("Pending order disappeared")
        return stored

    async def _retrieve_session(self, session_id: str) -> Any:
        if self.stripe_client is None:
            raise PaymentNotConfiguredError("Stripe is not configured")
        return await self._stripe_call(
            lambda: self.stripe_client.v1.checkout.sessions.retrieve(session_id)
        )

    async def _ensure_checkout(self, stored: StoredPosOrder) -> StoredPosOrder:
        attempt = stored.latest_attempt
        now = self._now()
        if attempt.status == "creating":
            if now - _aware(attempt.created_at) >= CREATING_ATTEMPT_LIFETIME:
                raise PaymentProviderError(
                    "Payment attempt requires manual reconciliation"
                )
            return await self._create_stripe_session(stored.order, attempt)

        if attempt.status in {"paid"} or stored.status in {"paid", "queued"}:
            return stored

        if attempt.status == "open":
            if attempt.expires_at is None or _aware(attempt.expires_at) > now:
                return stored
            authoritative = await self._retrieve_session(attempt.stripe_session_id or "")
            if _value(authoritative, "status") != "expired":
                return stored
            await self.store.mark_attempt_expired(
                attempt.stripe_session_id or "", updated_at=now
            )

        attempt_id = str(uuid4())
        await self.store.add_attempt(
            stored.order.orderID,
            attempt_id=attempt_id,
            idempotency_key=f"checkout-session:{attempt_id}",
            created_at=now,
        )
        refreshed = await self.store.get_order(stored.order.orderID)
        if refreshed is None:
            raise RuntimeError("Pending order disappeared")
        new_attempt = next(
            attempt
            for attempt in refreshed.attempts
            if attempt.attempt_id == attempt_id
        )
        return await self._create_stripe_session(refreshed.order, new_attempt)

    def _checkout_response(
        self, stored: StoredPosOrder, *, demo_blocked: bool = False
    ) -> CheckoutResponse:
        attempt = stored.latest_attempt
        if not attempt.is_demo and (
            not attempt.stripe_session_id or not attempt.checkout_url
        ):
            raise PaymentProviderError("Checkout session is not available")
        return CheckoutResponse(
            orderID=stored.order.orderID,
            status=stored.status,
            currency="gbp",
            totalMinor=stored.order.totalMinor,
            items=[item.public() for item in stored.order.items],
            isDemo=attempt.is_demo,
            demoBlocked=demo_blocked,
            stripeSessionID=None if attempt.is_demo else attempt.stripe_session_id,
            checkoutURL=None if attempt.is_demo else attempt.checkout_url,
        )

    async def _effective_demo_mode(self) -> bool:
        return self.settings.allow_demo_mode and await self.store.demo_mode_enabled()

    def _validate_attempt_provenance(self, stored: StoredPosOrder) -> None:
        attempt_modes = {attempt.is_demo for attempt in stored.attempts}
        if len(attempt_modes) != 1:
            raise RuntimeError("Payment attempt provenance is inconsistent")

    async def create_checkout(self, submitted: PosOrderInput) -> CheckoutResponse:
        canonical = self._canonicalize(submitted)
        async with self.lock:
            stored = await self.store.get_order(canonical.orderID)
            if stored is not None:
                if not self._same_order(stored.order, canonical):
                    raise PosConflictError(
                        "Order identifier already has different content"
                    )
            else:
                identifiers = {item.identifier for item in canonical.items}
                attempt_id = str(uuid4())
                is_demo = await self._effective_demo_mode()

                async def persist_pending() -> None:
                    if await self.store.item_identifiers_exist(identifiers):
                        raise PosConflictError(
                            "An order or drink identifier is already in use"
                        )
                    await self.store.add_pending(
                        canonical,
                        attempt_id=attempt_id,
                        idempotency_key=(
                            f"demo-payment:{attempt_id}"
                            if is_demo
                            else f"checkout-session:{attempt_id}"
                        ),
                        created_at=self._now(),
                        is_demo=is_demo,
                    )

                if not await self.queue_runtime.reserve_external_order(
                    canonical.orderID, identifiers, persist_pending
                ):
                    raise PosConflictError(
                        "An order or drink identifier is already in use"
                    )
                stored = await self.store.get_order(canonical.orderID)
                if stored is None:
                    raise RuntimeError("Pending order was not persisted")
            self._validate_attempt_provenance(stored)
            if stored.latest_attempt.is_demo:
                effective = await self._effective_demo_mode()
                return self._checkout_response(
                    stored,
                    demo_blocked=stored.status != "queued" and not effective,
                )
            ready = await self._ensure_checkout(stored)
            return self._checkout_response(ready)

    def construct_webhook_event(self, payload: bytes, signature: str) -> Any:
        if not self.settings.stripe_webhook_secret:
            raise PaymentNotConfiguredError("Stripe webhook is not configured")
        try:
            return stripe.Webhook.construct_event(
                payload, signature, self.settings.stripe_webhook_secret
            )
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise PaymentVerificationError("Invalid Stripe webhook") from error

    def _attempt_for_session(
        self, stored: StoredPosOrder, session_id: str
    ) -> StoredPaymentAttempt:
        attempt = next(
            (
                item
                for item in stored.attempts
                if item.stripe_session_id == session_id
            ),
            None,
        )
        if attempt is None:
            raise PaymentVerificationError("Unknown checkout session")
        return attempt

    def _validate_session(
        self, session: Any, stored: StoredPosOrder, attempt: StoredPaymentAttempt
    ) -> str:
        session_id = _value(session, "id")
        metadata = _value(session, "metadata", {}) or {}
        payment_intent = _value(session, "payment_intent")
        payment_intent_id = _value(payment_intent, "id", payment_intent)
        valid = (
            session_id == attempt.stripe_session_id
            and _value(session, "mode") == "payment"
            and _value(session, "payment_status") == "paid"
            and _value(session, "currency") == stored.order.currency
            and _value(session, "amount_total") == stored.order.totalMinor
            and _value(session, "client_reference_id") == stored.order.orderID
            and _value(metadata, "order_id") == stored.order.orderID
            and _value(metadata, "attempt_id") == attempt.attempt_id
            and isinstance(payment_intent_id, str)
            and bool(payment_intent_id)
        )
        if not valid:
            raise PaymentVerificationError("Checkout session did not reconcile")
        return payment_intent_id

    async def _fulfill(self, stored: StoredPosOrder) -> StoredPosOrder:
        if stored.status == "queued":
            return stored
        self._validate_attempt_provenance(stored)
        if stored.latest_attempt.is_demo and not await self._effective_demo_mode():
            raise DemoModeNotAllowedError("Demo mode is disabled")
        order = Order(
            orderID=stored.order.orderID,
            customer=stored.order.customer,
            drinks=[item.drink.model_copy(deep=True) for item in stored.order.items],
        )
        await self.queue_runtime.intake(
            order, reserved_pos_order_id=stored.order.orderID
        )
        await self.store.mark_queued(order.orderID, queued_at=self._now())
        queued = await self.store.get_order(order.orderID)
        if queued is None:
            raise RuntimeError("Queued order disappeared")
        return queued

    async def handle_webhook_event(self, event: Any) -> None:
        event_type = _value(event, "type")
        if event_type not in {
            "checkout.session.completed",
            "checkout.session.expired",
        }:
            return
        event_data = _value(event, "data", {}) or {}
        event_session = _value(event_data, "object")
        session_id = _value(event_session, "id")
        if not isinstance(session_id, str) or not session_id:
            raise PaymentVerificationError("Webhook session is missing")

        async with self.lock:
            stored = await self.store.get_order_by_session(session_id)
            if stored is None:
                raise PaymentVerificationError("Unknown checkout session")
            attempt = self._attempt_for_session(stored, session_id)

            if event_type == "checkout.session.expired":
                metadata = _value(event_session, "metadata", {}) or {}
                if (
                    _value(event_session, "status") != "expired"
                    or _value(event_session, "id") != attempt.stripe_session_id
                    or _value(event_session, "client_reference_id")
                    != stored.order.orderID
                    or _value(metadata, "order_id") != stored.order.orderID
                    or _value(metadata, "attempt_id") != attempt.attempt_id
                ):
                    raise PaymentVerificationError(
                        "Expired checkout session did not reconcile"
                    )
                await self.store.mark_attempt_expired(
                    session_id, updated_at=self._now()
                )
                return

            if _value(event_session, "payment_status") != "paid":
                return
            authoritative = await self._retrieve_session(session_id)
            payment_intent_id = self._validate_session(
                authoritative, stored, attempt
            )
            if stored.status == "pending_payment":
                stored = await self.store.mark_paid(
                    session_id,
                    payment_intent_id=payment_intent_id,
                    paid_at=self._now(),
                )
            elif attempt.status != "paid":
                raise PaymentVerificationError(
                    "Order was paid through another checkout session"
                )
            await self._fulfill(stored)

    def _receipt(
        self, stored: StoredPosOrder, *, demo_blocked: bool = False
    ) -> ReceiptResponse:
        return ReceiptResponse(
            orderID=stored.order.orderID,
            customer=stored.order.customer,
            status=stored.status,
            checkoutStatus=stored.latest_attempt.status,
            currency="gbp",
            totalMinor=stored.order.totalMinor,
            items=[item.public() for item in stored.order.items],
            createdAt=stored.created_at,
            paidAt=stored.paid_at,
            queuedAt=stored.queued_at,
            isDemo=stored.latest_attempt.is_demo,
            demoBlocked=demo_blocked,
        )

    async def receipt(self, session_id: str) -> ReceiptResponse | None:
        async with self.lock:
            stored = await self.store.get_order_by_session(session_id)
            if stored is None:
                return None
            self._validate_attempt_provenance(stored)
            if stored.latest_attempt.is_demo:
                return None
            if stored.status == "paid":
                stored = await self._fulfill(stored)
            return self._receipt(stored)

    async def demo_receipt(self, order_id: str) -> ReceiptResponse | None:
        async with self.lock:
            stored = await self.store.get_order(order_id)
            if stored is None:
                return None
            self._validate_attempt_provenance(stored)
            if not stored.latest_attempt.is_demo:
                return None
            effective = await self._effective_demo_mode()
            if stored.status == "paid" and effective:
                stored = await self._fulfill(stored)
            return self._receipt(
                stored,
                demo_blocked=stored.status != "queued" and not effective,
            )

    async def submit_demo_payment(self, order_id: str) -> ReceiptResponse:
        async with self.lock:
            if not await self._effective_demo_mode():
                raise DemoModeNotAllowedError("Demo mode is disabled")
            stored = await self.store.get_order(order_id)
            if stored is None:
                raise DemoPaymentError("Demo order not found")
            self._validate_attempt_provenance(stored)
            attempt = stored.latest_attempt
            if not attempt.is_demo:
                raise DemoPaymentError("Order is not a demo payment")
            if stored.status == "pending_payment":
                stored = await self.store.mark_demo_paid(
                    attempt.attempt_id, paid_at=self._now()
                )
            stored = await self._fulfill(stored)
            return self._receipt(stored)

    async def configuration(self) -> DemoModeResponse:
        async with self.lock:
            return await self._configuration_locked()

    async def _configuration_locked(self) -> DemoModeResponse:
        persisted = await self.store.demo_mode_enabled()
        return DemoModeResponse(
            demoModeEnabled=self.settings.allow_demo_mode and persisted,
            demoModePersisted=persisted,
            demoModeAvailable=self.settings.allow_demo_mode,
        )

    async def set_demo_mode(self, enabled: bool) -> DemoModeResponse:
        async with self.lock:
            persisted = await self.store.demo_mode_enabled()
            if enabled and not self.settings.allow_demo_mode:
                raise DemoModeNotAllowedError(
                    "Demo mode is not available on this server"
                )
            if not enabled and persisted and self.settings.allow_demo_mode:
                await self._recover_paid_orders_locked()
            if enabled != persisted:
                await self.store.set_demo_mode_enabled(enabled)
            if enabled:
                await self._recover_paid_orders_locked()
            return await self._configuration_locked()

    async def recover_paid_orders(self) -> None:
        async with self.lock:
            await self._recover_paid_orders_locked()

    async def _recover_paid_orders_locked(self) -> None:
        effective = await self._effective_demo_mode()
        for stored in await self.store.paid_unqueued():
            self._validate_attempt_provenance(stored)
            if stored.latest_attempt.is_demo and not effective:
                continue
            await self._fulfill(stored)
