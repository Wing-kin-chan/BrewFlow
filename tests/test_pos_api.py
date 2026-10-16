import json
from pathlib import Path

from fastapi.testclient import TestClient
import stripe

from brewflow.application import create_app
from brewflow.settings import PaymentSettings, load_catalog_settings, load_queue_settings
from tests.test_payments import (
    DRINK_ID,
    ORDER_ID,
    Clock,
    FakeStripeClient,
    paid_event,
)


def app_client(
    tmp_path: Path,
    fake: FakeStripeClient | None = None,
    *,
    allow_demo_mode: bool = False,
) -> TestClient:
    frontend = tmp_path / "dist"
    frontend.mkdir(parents=True, exist_ok=True)
    (frontend / "assets").mkdir(exist_ok=True)
    (frontend / "index.html").write_text("<div id='app'></div>", encoding="utf-8")
    return TestClient(
        create_app(
            database_uri=f"sqlite+aiosqlite:///{tmp_path / 'pos-api.db'}",
            frontend_dist=frontend,
            queue_settings=load_queue_settings(),
            catalog_settings=load_catalog_settings(),
            payment_settings=PaymentSettings(
                stripe_secret_key="sk_test_placeholder" if fake else None,
                stripe_webhook_secret="whsec_placeholder",
                checkout_return_base_url="http://127.0.0.1:8000",
                stripe_timeout_seconds=1,
                allow_demo_mode=allow_demo_mode,
            ),
            stripe_client=fake,
        )
    )


def raw_order(*, customer="Ada") -> dict:
    return {
        "orderID": ORDER_ID,
        "customer": customer,
        "items": [
            {
                "identifier": DRINK_ID,
                "catalogItemID": "latte",
                "milk": "Soy",
                "texture": "Extra Wet",
                "temperature": "Normal",
                "options": ["Decaf"],
            }
        ],
    }


def signed(payload: bytes) -> str:
    return stripe.WebhookSignature.generate_signature_header(
        payload.decode("utf-8"), "whsec_placeholder"
    )


def test_pos_checkout_verified_webhook_receipt_and_queue_end_to_end(tmp_path):
    fake = FakeStripeClient(Clock())
    with app_client(tmp_path, fake) as client:
        catalog = client.get("/api/pos/catalog")
        assert catalog.status_code == 200
        assert catalog.json()["currency"] == "gbp"
        assert len(catalog.json()["items"]) == 12

        checkout = client.post("/api/pos/orders", json=raw_order())
        assert checkout.status_code == 201
        body = checkout.json()
        assert body["totalMinor"] == 400
        assert client.get("/api/queue/state").json()["totalDrinks"] == 0

        session = fake.sessions.pay(body["stripeSessionID"])
        event = paid_event(session)
        payload = json.dumps(event, separators=(",", ":")).encode()
        webhook = client.post(
            "/api/payments/stripe/webhook",
            content=payload,
            headers={"Stripe-Signature": signed(payload)},
        )
        assert webhook.status_code == 200
        assert client.get("/api/queue/state").json()["totalDrinks"] == 1

        receipt = client.get(f"/api/pos/receipts/{body['stripeSessionID']}")
        assert receipt.status_code == 200
        assert set(receipt.json()) == {
            "orderID",
            "customer",
            "status",
            "checkoutStatus",
            "currency",
            "totalMinor",
            "items",
            "createdAt",
            "paidAt",
            "queuedAt",
            "isDemo",
            "demoBlocked",
        }
        assert receipt.json()["status"] == "queued"
        serialized = receipt.text
        assert "checkoutURL" not in serialized
        assert "idempotency" not in serialized
        assert "paymentIntent" not in serialized


def test_pos_api_rejects_client_prices_conflicts_and_unconfigured_stripe(tmp_path):
    with app_client(tmp_path) as client:
        payload = raw_order()
        payload["items"][0]["unitAmountMinor"] = 1
        assert client.post("/api/pos/orders", json=payload).status_code == 422

        assert client.post("/api/pos/orders", json=raw_order()).status_code == 503

    fake = FakeStripeClient(Clock())
    with app_client(tmp_path / "configured", fake) as configured:
        assert configured.post("/api/pos/orders", json=raw_order()).status_code == 201
        assert configured.post(
            "/api/pos/orders", json=raw_order(customer="Grace")
        ).status_code == 409


def test_webhook_rejects_missing_invalid_and_oversized_signatures(tmp_path):
    fake = FakeStripeClient(Clock())
    with app_client(tmp_path, fake) as client:
        assert client.post("/api/payments/stripe/webhook", content=b"{}").status_code == 400
        assert client.post(
            "/api/payments/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "invalid"},
        ).status_code == 400
        assert client.post(
            "/api/payments/stripe/webhook",
            content=b"x" * 1_048_577,
            headers={"Stripe-Signature": "invalid"},
        ).status_code == 413

        irrelevant = json.dumps(
            {"id": "evt_irrelevant", "type": "customer.created", "data": {}}
        ).encode()
        assert client.post(
            "/api/payments/stripe/webhook",
            content=irrelevant,
            headers={"Stripe-Signature": signed(irrelevant)},
        ).status_code == 200


def test_signed_but_mismatched_session_is_rejected_without_queueing(tmp_path):
    fake = FakeStripeClient(Clock())
    with app_client(tmp_path, fake) as client:
        checkout = client.post("/api/pos/orders", json=raw_order()).json()
        session = fake.sessions.pay(checkout["stripeSessionID"])
        session["amount_total"] = 1
        event = paid_event(session)
        payload = json.dumps(event, separators=(",", ":")).encode()
        response = client.post(
            "/api/payments/stripe/webhook",
            content=payload,
            headers={"Stripe-Signature": signed(payload)},
        )
        assert response.status_code == 400
        assert client.get("/api/queue/state").json()["totalDrinks"] == 0
        receipt = client.get(
            f"/api/pos/receipts/{checkout['stripeSessionID']}"
        ).json()
        assert receipt["status"] == "pending_payment"


def test_receipt_requires_opaque_known_session_and_pages_are_explicit(tmp_path):
    fake = FakeStripeClient(Clock())
    with app_client(tmp_path, fake) as client:
        assert client.get("/api/pos/receipts/cs_unknown").status_code == 404
        assert client.get("/api/pos").status_code == 200
        assert client.get("/api/receipt?session_id=cs_unknown").status_code == 200
        assert client.get(f"/api/pos/receipts/{ORDER_ID}").status_code == 422


def test_demo_configuration_checkout_submit_and_queue_are_server_authoritative(tmp_path):
    with app_client(tmp_path, allow_demo_mode=True) as client:
        initial = client.get("/api/configuration/demo-mode")
        assert initial.status_code == 200
        assert initial.json() == {
            "demoModeEnabled": False,
            "demoModePersisted": False,
            "demoModeAvailable": True,
        }
        enabled = client.put(
            "/api/configuration/demo-mode", json={"demoModeEnabled": True}
        )
        assert enabled.status_code == 200
        assert enabled.json()["demoModeEnabled"] is True

        forged = raw_order()
        forged["isDemo"] = True
        assert client.post("/api/pos/orders", json=forged).status_code == 422

        checkout = client.post("/api/pos/orders", json=raw_order())
        assert checkout.status_code == 201
        assert checkout.json()["isDemo"] is True
        assert checkout.json()["stripeSessionID"] is None
        assert checkout.json()["checkoutURL"] is None

        direct = {
            "orderID": ORDER_ID,
            "customer": "Ada",
            "drinks": [
                {
                    "identifier": DRINK_ID,
                    "orderID": ORDER_ID,
                    "customer": "Ada",
                    "drink": "Latte",
                    "milk": "Soy",
                    "milk_volume": 2,
                    "shots": 2,
                    "temperature": "Normal",
                    "texture": "Extra Wet",
                    "options": ["Decaf"],
                }
            ],
        }
        assert client.post("/api/queue/orders", json=direct).status_code == 409

        first = client.post(f"/api/pos/orders/{ORDER_ID}/demo-payment")
        second = client.post(f"/api/pos/orders/{ORDER_ID}/demo-payment")
        assert first.status_code == second.status_code == 200
        assert first.json()["status"] == second.json()["status"] == "queued"
        assert first.json()["isDemo"] is True
        assert client.get("/api/queue/state").json()["totalDrinks"] == 1

        second_order_id = "00000000-0000-4000-8000-000000000011"
        second_drink_id = "00000000-0000-4000-8000-000000000012"
        second_payload = raw_order(customer="Grace")
        second_payload["orderID"] = second_order_id
        second_payload["items"][0]["identifier"] = second_drink_id
        second_checkout = client.post("/api/pos/orders", json=second_payload)
        assert second_checkout.status_code == 201
        assert second_checkout.json()["orderID"] == second_order_id
        second_payment = client.post(
            f"/api/pos/orders/{second_order_id}/demo-payment"
        )
        assert second_payment.status_code == 200
        assert second_payment.json()["status"] == "queued"
        assert client.get("/api/queue/state").json()["totalDrinks"] == 2

        client.post("/api/queue/completions", json={"drinkIDs": [DRINK_ID]})
        history = client.get("/api/history/orders").json()
        assert history["totalDrinks"] == 1
        assert history["orders"][0]["orderID"] == ORDER_ID


def test_demo_toggle_requires_gate_and_disabled_attempt_cannot_submit(tmp_path):
    with app_client(tmp_path) as client:
        response = client.put(
            "/api/configuration/demo-mode", json={"demoModeEnabled": True}
        )
        assert response.status_code == 403
        assert client.get("/api/configuration/demo-mode").json()[
            "demoModeEnabled"
        ] is False

    with app_client(tmp_path / "frozen", allow_demo_mode=True) as client:
        client.put("/api/configuration/demo-mode", json={"demoModeEnabled": True})
        checkout = client.post("/api/pos/orders", json=raw_order()).json()
        client.put("/api/configuration/demo-mode", json={"demoModeEnabled": False})
        response = client.post(f"/api/pos/orders/{ORDER_ID}/demo-payment")
        assert response.status_code == 409
        receipt = client.get(f"/api/pos/demo-receipts/{ORDER_ID}").json()
        assert receipt["status"] == "pending_payment"
        assert receipt["demoBlocked"] is True
        assert checkout["isDemo"] is True


def test_uuid7_demo_order_can_submit_and_load_receipt_with_canonical_route_id(tmp_path):
    order_id = "018f4f5e-7b3c-7a1f-8c2d-123456789abc"
    drink_id = "018f4f5e-7b3c-7a1f-8c2d-123456789abd"
    payload = raw_order()
    payload["orderID"] = order_id
    payload["items"][0]["identifier"] = drink_id

    with app_client(tmp_path, allow_demo_mode=True) as client:
        client.put("/api/configuration/demo-mode", json={"demoModeEnabled": True})
        checkout = client.post("/api/pos/orders", json=payload)
        assert checkout.status_code == 201
        assert checkout.json()["orderID"] == order_id

        submitted = client.post(
            f"/api/pos/orders/{order_id.upper()}/demo-payment"
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "queued"
        assert submitted.json()["orderID"] == order_id

        receipt = client.get(f"/api/pos/demo-receipts/{order_id.upper()}")
        assert receipt.status_code == 200
        assert receipt.json()["status"] == "queued"
        assert receipt.json()["orderID"] == order_id

        assert client.post(
            "/api/pos/orders/not-a-uuid/demo-payment"
        ).status_code == 422
        assert client.get(
            "/api/pos/demo-receipts/not-a-uuid"
        ).status_code == 422
