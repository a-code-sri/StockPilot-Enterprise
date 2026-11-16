"""FreshBasket Online shop server, against an in-memory fake of the StockPilot API."""

import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest
from fastapi import HTTPException

from client_app import server


class FakeStockPilot:
    def __init__(self):
        today = date.today()
        self.items = {
            1: {"id": 1, "name": "Shimla Apple (kg)", "quantity": 10, "price": 180.0, "status": "under_use",
                "expiry_date": (today + timedelta(days=5)).isoformat()},
            2: {"id": 2, "name": "Banana (dozen)", "quantity": 4, "price": 60.0, "status": "under_use",
                "expiry_date": (today - timedelta(days=1)).isoformat()},  # past its date
        }
        self.deliveries: dict[str, dict] = {}
        self.transactions: list[dict] = []
        self.logins = 0
        self.expire_next = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path == "/auth/login":
            self.logins += 1
            return httpx.Response(200, json={"access_token": f"t{self.logins}", "token_type": "bearer"})
        if self.expire_next:
            self.expire_next = False
            return httpx.Response(401, json={"detail": "Invalid or expired token"})
        body = json.loads(request.content) if request.content else None
        if path == "/inventory/" and method == "GET":
            return httpx.Response(200, json=list(self.items.values()))
        if path == "/delivery/" and method == "POST":
            self.deliveries[body["order_id"]] = {**body, "status": "pending"}
            return httpx.Response(201, json={"order_id": body["order_id"]})
        if path.startswith("/delivery/"):
            order_id = path.split("/")[2]
            d = self.deliveries.get(order_id)
            if d is None:
                return httpx.Response(404, json={"detail": "Delivery not found"})
            if path.endswith("/logs"):
                return httpx.Response(200, json=[{"id": 1, "from_status": None, "to_status": "pending",
                                                  "remark": None, "timestamp": "2026-01-01T10:00:00Z"}])
            if path.endswith("/status"):
                d["status"] = body["status"]
                return httpx.Response(200, json={"status": d["status"]})
            return httpx.Response(200, json={"order_id": order_id, "status": d["status"]})
        if path == "/accounts/" and method == "POST":
            self.transactions.append(body)
            return httpx.Response(201, json=body)
        return httpx.Response(404, json={"detail": f"no fake for {method} {path}"})


@pytest.fixture
def env(tmp_path):
    fake = FakeStockPilot()
    sp = server.StockPilot("http://sp", "shop", "pw", transport=httpx.MockTransport(fake.handler))
    shop = server.Shop(sp, server.OrderStore(tmp_path), server.Hub())
    return fake, shop


def run(coro):
    return asyncio.run(coro)


def checkout(**items):
    return server.CheckoutIn(name="Priya Sharma", phone="98200 11234", address="12 Lake View Road",
                             items=[server.CartLine(item_id=int(k[1:]), quantity=v) for k, v in items.items()])


def test_catalogue_names_units_and_hides_expired_stock(env):
    fake, shop = env
    fruits = {f["id"]: f for f in run(shop.catalogue())}
    assert fruits[1]["name"] == "Shimla Apple" and fruits[1]["unit"] == "kg" and fruits[1]["emoji"] == "🍎"
    assert fruits[1]["available"] == 10
    assert fruits[2]["available"] == 0  # expired fruit is not for sale


def test_order_creates_stock_linked_delivery_and_reserves_stock(env):
    fake, shop = env
    order = run(shop.place_order(checkout(i1=3)))
    sent = fake.deliveries[order["order_id"]]
    assert sent["items"] == [{"product_name": "Shimla Apple (kg)", "quantity": 3, "unit_price": 180.0, "inventory_item_id": 1}]
    assert order["total"] == 540
    # Not yet dispatched, so StockPilot still has 10, but only 7 can be sold.
    assert {f["id"]: f["available"] for f in run(shop.catalogue())}[1] == 7
    with pytest.raises(HTTPException) as e:
        run(shop.place_order(checkout(i1=8)))
    assert e.value.status_code == 409 and "Only 7" in e.value.detail


def test_delivered_order_is_paid_once(env):
    fake, shop = env
    order = run(shop.place_order(checkout(i1=2)))
    fake.deliveries[order["order_id"]]["status"] = "delivered"

    async def both():  # tracking page and sync loop at the same moment
        await asyncio.gather(shop.sync_orders(), shop.track(order["order_id"]))
        await shop.sync_orders()

    run(both())
    assert len(fake.transactions) == 1
    t = fake.transactions[0]
    assert t["transaction_type"] == "credit" and t["amount"] == 360 and t["category"] == "Online sales"
    assert shop.store.orders[order["order_id"]]["paid"] is True


def test_cancel_only_before_dispatch(env):
    fake, shop = env
    a = run(shop.place_order(checkout(i1=1)))
    assert run(shop.cancel(a["order_id"]))["status"] == "cancelled"
    b = run(shop.place_order(checkout(i1=1)))
    fake.deliveries[b["order_id"]]["status"] = "out_for_delivery"
    with pytest.raises(HTTPException) as e:
        run(shop.cancel(b["order_id"]))
    assert e.value.status_code == 409


def test_expired_token_signs_in_again(env):
    fake, shop = env
    run(shop.catalogue())
    fake.expire_next = True
    run(shop.catalogue())
    assert fake.logins == 2


def test_unknown_order_is_404(env):
    _, shop = env
    with pytest.raises(HTTPException) as e:
        run(shop.track("FB-NOPE"))
    assert e.value.status_code == 404


def test_orders_survive_a_restart(env, tmp_path):
    _, shop = env
    order = run(shop.place_order(checkout(i1=1)))
    assert order["order_id"] in server.OrderStore(tmp_path).orders
