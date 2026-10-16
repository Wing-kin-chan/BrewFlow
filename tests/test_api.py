from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brewflow.application import create_app
from tests.conftest import make_order


def make_client(tmp_path: Path, queue_settings) -> TestClient:
    frontend = tmp_path / "dist"
    frontend.mkdir(exist_ok=True)
    (frontend / "assets").mkdir(exist_ok=True)
    (frontend / "index.html").write_text(
        '<!doctype html><div id="app"></div>', encoding="utf-8"
    )
    app = create_app(
        database_uri=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}",
        frontend_dist=frontend,
        queue_settings=queue_settings,
    )
    return TestClient(app)


def raw_order(order_id: str, drink_id: str, *, options: list[str] | None = None) -> dict:
    return {
        "orderID": order_id,
        "customer": "Ada",
        "drinks": [
            {
                "identifier": drink_id,
                "drink": "Latte",
                "milk": "Whole",
                "milk_volume": 2,
                "shots": 2,
                "temperature": "Normal",
                "texture": "Wet",
                "options": options or [],
            }
        ],
    }


def test_page_routes_are_explicit_and_data_routes_are_json(tmp_path, queue_settings):
    with make_client(tmp_path, queue_settings) as client:
        redirect = client.get("/", follow_redirects=False)
        assert redirect.status_code in {302, 307}
        assert redirect.headers["location"] == "/api/queue"
        assert client.get("/api/queue").headers["content-type"].startswith("text/html")
        assert client.get("/api/history").headers["content-type"].startswith("text/html")
        assert client.get("/api/queue/state").headers["content-type"].startswith("application/json")
        assert client.get("/api/menu").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404


def test_intake_completion_history_and_validation(tmp_path, queue_settings):
    with make_client(tmp_path, queue_settings) as client:
        order = make_order("order-1")
        submitted_time = order.timeReceived
        response = client.post("/api/queue/orders", json=order.model_dump(mode="json"))
        assert response.status_code == 201
        assert response.json()["status"] == "accepted"
        assert response.json()["queue"]["totalDrinks"] == 1
        assert response.json()["queue"]["items"][0]["drinks"][0]["timeReceived"] != submitted_time.isoformat()

        duplicate = client.post("/api/queue/orders", json=order.model_dump(mode="json"))
        assert duplicate.status_code == 201
        assert duplicate.json()["status"] == "duplicate"
        assert duplicate.json()["queue"]["totalDrinks"] == 1

        completion = client.post(
            "/api/queue/completions", json={"drinkIDs": ["order-1-drink-1"]}
        )
        assert completion.status_code == 200
        assert completion.json()["totalDrinks"] == 0
        repeated = client.post(
            "/api/queue/completions", json={"drinkIDs": ["order-1-drink-1"]}
        )
        assert repeated.status_code == 200
        assert repeated.json()["revision"] == completion.json()["revision"]

        history = client.get("/api/history/orders").json()
        assert history["totalOrders"] == 1
        assert history["orders"][0]["orderID"] == "order-1"

        invalid = order.model_copy(deep=True)
        invalid.orderID = "order-2"
        invalid.drinks[0].orderID = "order-2"
        invalid.drinks[0].identifier = "invalid-drink"
        invalid.drinks[0].milk = "Mystery"
        assert client.post("/api/queue/orders", json=invalid.model_dump(mode="json")).status_code == 422

        invalid_texture = order.model_dump(mode="json")
        invalid_texture["orderID"] = "order-3"
        invalid_texture["drinks"][0]["identifier"] = "invalid-texture"
        invalid_texture["drinks"][0]["orderID"] = "order-3"
        invalid_texture["drinks"][0]["texture"] = "Foamy"
        assert client.post("/api/queue/orders", json=invalid_texture).status_code == 422

        invalid_drink = order.model_dump(mode="json")
        invalid_drink["orderID"] = "order-4"
        invalid_drink["drinks"][0]["identifier"] = "invalid-drink-name"
        invalid_drink["drinks"][0]["orderID"] = "order-4"
        invalid_drink["drinks"][0]["drink"] = "Mystery"
        assert client.post("/api/queue/orders", json=invalid_drink).status_code == 422


def test_two_websocket_clients_receive_intake_and_completion_events(tmp_path, queue_settings):
    with make_client(tmp_path, queue_settings) as client:
        with client.websocket_connect("/api/queue/events") as first:
            with client.websocket_connect("/api/queue/events") as second:
                assert first.receive_json()["type"] == "queue.connected"
                assert second.receive_json()["type"] == "queue.connected"

                order = make_order("order-1")
                client.post("/api/queue/orders", json=order.model_dump(mode="json"))
                assert first.receive_json()["type"] == "queue.changed"
                assert second.receive_json()["type"] == "queue.changed"

                client.post(
                    "/api/queue/completions",
                    json={"drinkIDs": ["order-1-drink-1"]},
                )
                assert first.receive_json()["revision"] == 2
                assert second.receive_json()["revision"] == 2
                assert len(client.app.state.queue_runtime.events.connections) == 2
            assert len(client.app.state.queue_runtime.events.connections) == 1
        assert len(client.app.state.queue_runtime.events.connections) == 0


def test_raw_intake_requires_ids_rejects_conflicting_ownership_and_retries_cleanly(
    tmp_path, queue_settings
):
    with make_client(tmp_path, queue_settings) as client:
        valid = raw_order("raw-order", "raw-drink")
        assert client.post("/api/queue/orders", json=valid).json()["status"] == "accepted"
        assert client.post("/api/queue/orders", json=valid).json()["status"] == "duplicate"

        missing_order_id = raw_order("unused", "missing-order")
        del missing_order_id["orderID"]
        assert client.post("/api/queue/orders", json=missing_order_id).status_code == 422

        empty_order_id = raw_order("", "empty-order")
        assert client.post("/api/queue/orders", json=empty_order_id).status_code == 422

        missing_drink_id = raw_order("missing-drink-order", "unused")
        del missing_drink_id["drinks"][0]["identifier"]
        assert client.post("/api/queue/orders", json=missing_drink_id).status_code == 422

        empty_drink_id = raw_order("empty-drink-order", "")
        assert client.post("/api/queue/orders", json=empty_drink_id).status_code == 422

        whitespace_drink_id = raw_order("whitespace-drink-order", "   ")
        assert client.post("/api/queue/orders", json=whitespace_drink_id).status_code == 422

        wrong_order = raw_order("owner-order", "wrong-order")
        wrong_order["drinks"][0]["orderID"] = "another-order"
        assert client.post("/api/queue/orders", json=wrong_order).status_code == 422

        wrong_customer = raw_order("customer-order", "wrong-customer")
        wrong_customer["drinks"][0]["customer"] = "Grace"
        assert client.post("/api/queue/orders", json=wrong_customer).status_code == 422


def test_options_round_trip_and_raw_retry_survive_restart(tmp_path, queue_settings):
    submitted = raw_order(
        "options-order",
        "options-drink",
        options=["vanilla,caramel", "", "plain"],
    )
    with make_client(tmp_path, queue_settings) as client:
        assert client.post("/api/queue/orders", json=submitted).json()["status"] == "accepted"
        assert client.post("/api/queue/orders", json=submitted).json()["status"] == "duplicate"
        assert client.get("/api/queue/state").json()["items"][0]["drinks"][0]["options"] == submitted["drinks"][0]["options"]

    with make_client(tmp_path, queue_settings) as restarted:
        assert restarted.post("/api/queue/orders", json=submitted).json()["status"] == "duplicate"
        assert restarted.get("/api/queue/state").json()["items"][0]["drinks"][0]["options"] == submitted["drinks"][0]["options"]


@pytest.mark.parametrize("texture", ("Extra Wet", "Wet", "Dry", "Extra Dry"))
def test_all_product_textures_are_accepted_batched_and_temperature_sorted(
    tmp_path, queue_settings, texture
):
    submitted = raw_order(f"{texture}-order", f"{texture}-hot")
    submitted["drinks"][0]["texture"] = texture
    submitted["drinks"][0]["temperature"] = "Extra Hot"
    submitted["drinks"].append(
        {
            **submitted["drinks"][0],
            "identifier": f"{texture}-warm",
            "temperature": "Warm",
        }
    )

    with make_client(tmp_path, queue_settings) as client:
        response = client.post("/api/queue/orders", json=submitted)
        assert response.status_code == 201
        item = response.json()["queue"]["items"][0]
        assert item["kind"] == "batch"
        assert item["texture"] == texture
        assert [drink["temperature"] for drink in item["drinks"]] == ["Warm", "Extra Hot"]
