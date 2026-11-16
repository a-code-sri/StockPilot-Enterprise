"""
FreshBasket Online: the customer-facing web shop of a fruit seller that runs on StockPilot.

Shoppers never talk to StockPilot directly. This server signs in to StockPilot with a shop
service account and offers only what a shopper needs:

    GET  /api/catalogue             fruit with live availability (StockPilot inventory)
    POST /api/orders                checkout -> a StockPilot delivery with stock-linked items
    GET  /api/orders/{order_id}     order tracking with the status timeline
    POST /api/orders/{order_id}/cancel   cancel before the order leaves the shop
    WS   /ws                        live updates for the browser

It keeps one WebSocket open to StockPilot (/ws/realtime). When StockPilot reports an
inventory change, browsers reload the catalogue. When it reports a delivery change, the
server checks its open orders and pushes status changes to the shoppers watching them. When
an order is delivered, the payment is recorded in StockPilot Accounts, once per order.

    uvicorn server:app --port 8501          # from client_app/
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import string
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
import websockets
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger("freshbasket")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per API call is too noisy

HERE = Path(__file__).parent

SHOP_NAME = os.getenv("SHOP_NAME", "FreshBasket")
API_URL = os.getenv("STOCKPILOT_API_URL", "http://127.0.0.1:8000").rstrip("/")
WEB_URL = os.getenv("STOCKPILOT_WEB_URL", "http://localhost:8080").rstrip("/")
SHOP_USERNAME = os.getenv("SHOP_USERNAME", "")
SHOP_PASSWORD = os.getenv("SHOP_PASSWORD", "")
DATA_DIR = Path(os.getenv("SHOP_DATA_DIR", HERE / "data"))
DEMO_TOOLS = os.getenv("SHOP_DEMO_TOOLS", "true").lower() in ("1", "true", "yes")

# Without a realtime event (e.g. StockPilot's WebSocket is down) open orders are still
# re-checked this often.
ORDER_POLL_SECONDS = 20

OPEN_STATUSES = {"pending", "packed", "out_for_delivery", "failed"}
RESERVING_STATUSES = {"pending", "packed"}  # ordered but stock not yet taken off the shelf
CANCELLABLE = {"pending", "packed"}

# ---------------------------------------------------------------------------
# Catalogue presentation. StockPilot stores names like "Shimla Apple (kg)"; the shop adds a
# picture and a line of copy by keyword.
# ---------------------------------------------------------------------------

FRUIT_INFO = [
    ("apple", "🍎", "Crisp, juicy apples from the Shimla hills."),
    ("banana", "🍌", "Naturally ripened, sweet Robusta bananas."),
    ("mango", "🥭", "Ratnagiri Alphonso, the king of mangoes."),
    ("orange", "🍊", "Tangy Nagpur oranges, full of juice."),
    ("grape", "🍇", "Seedless green grapes from Nashik."),
    ("pomegranate", "❤️", "Deep red, sweet arils. Rich in iron."),
    ("papaya", "🧡", "Soft, ripe papaya. Great for breakfast."),
    ("watermelon", "🍉", "Cool and sweet, picked this week."),
    ("pineapple", "🍍", "Golden, sweet and tangy pineapple."),
    ("kiwi", "🥝", "Zesty kiwis packed with vitamin C."),
    ("guava", "🍐", "Pink-flesh guavas, lightly sweet."),
    ("strawberry", "🍓", "Mahabaleshwar strawberries, hand picked."),
    ("lemon", "🍋", "Fresh lemons for juice and cooking."),
    ("cherry", "🍒", "Dark, sweet cherries from Kashmir."),
    ("coconut", "🥥", "Tender coconuts with sweet water."),
    ("melon", "🍈", "Fragrant musk melon."),
    ("pear", "🍐", "Juicy, mellow pears."),
    ("peach", "🍑", "Soft, fragrant peaches."),
]

# Used by the demo tools: (StockPilot name, price, opening stock, shelf life in days).
STARTER_CATALOGUE = [
    ("Shimla Apple (kg)", 180, 60, 21),
    ("Banana (dozen)", 60, 80, 5),
    ("Alphonso Mango (dozen)", 450, 25, 7),
    ("Nagpur Orange (kg)", 120, 50, 14),
    ("Green Grapes (kg)", 140, 40, 6),
    ("Pomegranate (kg)", 220, 35, 20),
    ("Papaya (kg)", 50, 30, 5),
    ("Watermelon (kg)", 35, 70, 10),
    ("Pineapple (piece)", 80, 25, 7),
    ("Kiwi (piece)", 30, 90, 14),
    ("Guava (kg)", 90, 30, 6),
    ("Strawberry (box)", 250, 20, 4),
]
COST_RATIO = 0.65  # suppliers sell at about this share of the shop price
SUPPLIER = "Azadpur Mandi Traders"
DEMO_SHOPPERS = [
    ("Priya Sharma", "98200 11234", "12 Lake View Road, Indiranagar"),
    ("Rahul Verma", "99860 44321", "Flat 4B, Green Park Apartments"),
    ("Ananya Iyer", "90080 77890", "221 MG Road, near Metro Gate 2"),
    ("Mohammed Khan", "98450 66012", "7 Rose Street, Frazer Town"),
    ("Sneha Patil", "97310 55443", "B-18 Sunrise Layout, HSR"),
    ("Arjun Reddy", "96860 22109", "45 Temple Road, Malleshwaram"),
    ("Kavya Nair", "94480 99001", "3rd Cross, Koramangala 5th Block"),
    ("Vikram Singh", "98860 31415", "Villa 9, Palm Meadows"),
]
SLOTS = {
    "express": "Express, within 2 hours",
    "evening": "Today, 5 pm - 8 pm",
    "tomorrow": "Tomorrow, 8 am - 11 am",
}
PAYMENTS = {"cash": "Cash", "upi": "UPI", "card": "Card"}


def fruit_info(name: str) -> tuple[str, str]:
    low = name.lower()
    for key, emoji, blurb in FRUIT_INFO:
        if key in low:
            return emoji, blurb
    return "🧺", "Fresh from our partner farms."


def split_unit(name: str) -> tuple[str, str]:
    """'Shimla Apple (kg)' -> ('Shimla Apple', 'kg')."""
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", name)
    return (m.group(1), m.group(2)) if m else (name, "unit")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_order_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"FB-{utcnow():%y%m%d}-{suffix}"


# ---------------------------------------------------------------------------
# StockPilot API client
# ---------------------------------------------------------------------------


class StockPilotError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _detail(r: httpx.Response) -> str:
    try:
        d = r.json().get("detail")
    except Exception:
        return r.text[:300] or r.reason_phrase
    if isinstance(d, list):
        return "; ".join(str(x.get("msg", x)) for x in d)
    return str(d)


class StockPilot:
    """Signs in with the shop's service account and re-signs in when the token expires."""

    def __init__(self, base_url: str, username: str, password: str, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.http = httpx.AsyncClient(base_url=base_url, timeout=20, transport=transport)
        self.token: str | None = None
        self._lock = asyncio.Lock()

    async def ensure_token(self) -> str:
        async with self._lock:
            if not self.token:
                if not (self.username and self.password):
                    raise StockPilotError(503, "The shop has no StockPilot account configured (SHOP_USERNAME / SHOP_PASSWORD).")
                try:
                    r = await self.http.post("/auth/login", json={"username": self.username, "password": self.password})
                except httpx.HTTPError as e:
                    raise StockPilotError(503, f"StockPilot is not reachable at {self.base_url}.") from e
                if r.status_code != 200:
                    raise StockPilotError(503, f"StockPilot sign-in failed for '{self.username}': {_detail(r)}")
                self.token = r.json()["access_token"]
                logger.info("Signed in to StockPilot as %s", self.username)
            return self.token

    async def call(self, method: str, path: str, **kwargs) -> Any:
        for attempt in (1, 2):
            token = await self.ensure_token()
            try:
                r = await self.http.request(method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
            except httpx.HTTPError as e:
                raise StockPilotError(503, f"StockPilot is not reachable at {self.base_url}.") from e
            if r.status_code == 401 and attempt == 1:
                self.token = None  # expired or revoked: sign in again once
                continue
            if r.status_code >= 400:
                raise StockPilotError(r.status_code, _detail(r))
            return r.json() if r.content else None
        raise StockPilotError(503, "StockPilot rejected the shop's sign-in.")

    @property
    def ws_url(self) -> str:
        return re.sub(r"^http", "ws", self.base_url) + "/ws/realtime"

    async def close(self) -> None:
        await self.http.aclose()


# ---------------------------------------------------------------------------
# Orders placed through the shop (kept in a small JSON file)
# ---------------------------------------------------------------------------


class OrderStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "orders.json"
        self.orders: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            try:
                self.orders = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.exception("Could not read %s; starting with no orders", self.path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.orders, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def reserved(self) -> dict[int, int]:
        """Quantities in orders that are placed but not yet dispatched, by inventory item."""
        out: dict[int, int] = {}
        for o in self.orders.values():
            if o["status"] in RESERVING_STATUSES:
                for line in o["items"]:
                    out[line["item_id"]] = out.get(line["item_id"], 0) + line["quantity"]
        return out

    def open_orders(self) -> list[dict[str, Any]]:
        return [o for o in self.orders.values() if o["status"] in OPEN_STATUSES or (o["status"] == "delivered" and not o["paid"])]


# ---------------------------------------------------------------------------
# Browser connections
# ---------------------------------------------------------------------------


class Hub:
    """Browser WebSockets. Each one says which orders it is watching."""

    def __init__(self) -> None:
        self.clients: dict[WebSocket, set[str]] = {}
        self.stockpilot_live = False

    async def _send(self, ws: WebSocket, msg: dict[str, Any]) -> None:
        try:
            await ws.send_json(msg)
        except Exception:
            self.clients.pop(ws, None)

    async def broadcast(self, msg: dict[str, Any]) -> None:
        for ws in list(self.clients):
            await self._send(ws, msg)

    async def order_changed(self, order_id: str, status: str) -> None:
        for ws, watching in list(self.clients.items()):
            if order_id in watching:
                await self._send(ws, {"type": "order", "order_id": order_id, "status": status})

    async def set_live(self, live: bool) -> None:
        if live != self.stockpilot_live:
            self.stockpilot_live = live
            await self.broadcast({"type": "live", "connected": live})


# ---------------------------------------------------------------------------
# Shop logic
# ---------------------------------------------------------------------------


class CartLine(BaseModel):
    item_id: int
    quantity: int = Field(gt=0, le=99)


class CheckoutIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field(min_length=6, max_length=20)
    address: str = Field(min_length=5, max_length=300)
    slot: Literal["express", "evening", "tomorrow"] = "express"
    payment: Literal["cash", "upi", "card"] = "upi"
    note: str = Field(default="", max_length=200)
    items: list[CartLine] = Field(min_length=1, max_length=30)


class Shop:
    def __init__(self, sp: StockPilot, store: OrderStore, hub: Hub):
        self.sp = sp
        self.store = store
        self.hub = hub
        self.wake = asyncio.Event()
        self._sync_lock = asyncio.Lock()
        self._pay_lock = asyncio.Lock()

    # ---- catalogue ----

    async def catalogue(self) -> list[dict[str, Any]]:
        rows = await self.sp.call("GET", "/inventory/", params={"limit": 1000})
        reserved = self.store.reserved()
        today = date.today()
        out = []
        for r in rows:
            title, unit = split_unit(r["name"])
            emoji, blurb = fruit_info(r["name"])
            expiry = date.fromisoformat(r["expiry_date"]) if r.get("expiry_date") else None
            expired = expiry is not None and expiry < today
            available = 0 if expired else max(0, r["quantity"] - reserved.get(r["id"], 0))
            out.append({
                "id": r["id"], "name": title, "unit": unit, "price": float(r["price"]),
                "available": available, "emoji": emoji, "blurb": blurb,
                "fresh_days": None if expiry is None else (expiry - today).days,
            })
        out.sort(key=lambda f: (f["available"] == 0, f["name"]))
        return out

    # ---- orders ----

    async def place_order(self, data: CheckoutIn) -> dict[str, Any]:
        fruits = {f["id"]: f for f in await self.catalogue()}
        lines, wanted = [], {}
        for line in data.items:
            wanted[line.item_id] = wanted.get(line.item_id, 0) + line.quantity
        for item_id, qty in wanted.items():
            f = fruits.get(item_id)
            if f is None:
                raise HTTPException(409, "One of the items in your basket is no longer sold. Please remove it.")
            if qty > f["available"]:
                left = f["available"]
                msg = f"Sorry, {f['name']} is sold out." if left == 0 else f"Only {left} {f['unit']} of {f['name']} left."
                raise HTTPException(409, msg)
            lines.append({"item_id": item_id, "name": f["name"], "unit": f["unit"], "emoji": f["emoji"],
                          "quantity": qty, "price": f["price"]})

        order_id = new_order_id()
        remarks = " · ".join(filter(None, [
            "Online order", SLOTS[data.slot], f"Pay by {PAYMENTS[data.payment]} on delivery",
            f"Phone {data.phone}", f"Deliver to: {data.address}", f"Note: {data.note}" if data.note else "",
        ]))[:1000]
        await self.sp.call("POST", "/delivery/", json={
            "order_id": order_id,
            "customer_id": data.name.strip()[:80],
            "remarks": remarks,
            "items": [{"product_name": f"{line['name']} ({line['unit']})", "quantity": line["quantity"],
                       "unit_price": line["price"], "inventory_item_id": line["item_id"]} for line in lines],
        })
        order = {
            "order_id": order_id, "status": "pending", "created_at": utcnow().isoformat(),
            "customer": data.name.strip(), "phone": data.phone.strip(), "address": data.address.strip(),
            "slot": SLOTS[data.slot], "payment": PAYMENTS[data.payment], "note": data.note.strip(),
            "items": lines, "total": round(sum(line["price"] * line["quantity"] for line in lines), 2), "paid": False,
        }
        self.store.orders[order_id] = order
        self.store.save()
        logger.info("Order %s placed by %s (%s items, ₹%s)", order_id, order["customer"], len(lines), order["total"])
        await self.hub.broadcast({"type": "catalogue"})  # reserved stock changed
        return order

    def _known(self, order_id: str) -> dict[str, Any]:
        order = self.store.orders.get(order_id)
        if order is None:
            raise HTTPException(404, "We couldn't find that order.")
        return order

    async def track(self, order_id: str) -> dict[str, Any]:
        order = self._known(order_id)
        detail = await self.sp.call("GET", f"/delivery/{order_id}")
        logs = await self.sp.call("GET", f"/delivery/{order_id}/logs")
        await self._apply_status(order, detail["status"])
        return {
            **order,
            "can_cancel": order["status"] in CANCELLABLE,
            "timeline": [{"status": lg["to_status"], "at": lg["timestamp"], "remark": lg.get("remark")}
                         for lg in sorted(logs, key=lambda x: x["timestamp"])],
        }

    async def cancel(self, order_id: str) -> dict[str, Any]:
        order = self._known(order_id)
        current = (await self.sp.call("GET", f"/delivery/{order_id}"))["status"]
        if current not in CANCELLABLE:
            await self._apply_status(order, current)
            raise HTTPException(409, "This order has already left the shop and can't be cancelled.")
        await self.sp.call("PUT", f"/delivery/{order_id}/status", json={"status": "cancelled", "remark": "Cancelled by the customer"})
        await self._apply_status(order, "cancelled")
        return await self.track(order_id)

    async def _apply_status(self, order: dict[str, Any], status: str) -> None:
        if status != order["status"]:
            logger.info("Order %s: %s -> %s", order["order_id"], order["status"], status)
            order["status"] = status
            self.store.save()
            await self.hub.order_changed(order["order_id"], status)
            await self.hub.broadcast({"type": "catalogue"})  # reserved stock changed
        if status == "delivered" and not order["paid"]:
            async with self._pay_lock:  # a tracking request and the sync loop may race here
                if not order["paid"]:
                    await self._record_payment(order)

    async def _record_payment(self, order: dict[str, Any]) -> None:
        # The shopper pays the rider; the shop books the sale once. A failure here is
        # retried by the next sync, because unpaid delivered orders stay "open".
        try:
            await self.sp.call("POST", "/accounts/", json={
                "amount": order["total"], "transaction_type": "credit", "source_target": order["customer"][:200],
                "category": "Online sales", "remarks": f"Order {order['order_id']} · paid by {order['payment']} on delivery",
            })
        except StockPilotError as e:
            logger.warning("Could not record the payment for %s yet: %s", order["order_id"], e.detail)
            return
        order["paid"] = True
        self.store.save()
        logger.info("Recorded ₹%s payment for %s", order["total"], order["order_id"])

    async def sync_orders(self) -> None:
        async with self._sync_lock:
            for order in self.store.open_orders():
                try:
                    detail = await self.sp.call("GET", f"/delivery/{order['order_id']}")
                except StockPilotError as e:
                    if e.status == 404:  # deleted in StockPilot
                        order["status"] = "cancelled"
                        self.store.save()
                        continue
                    raise
                await self._apply_status(order, detail["status"])

    # ---- background loops ----

    async def realtime_loop(self) -> None:
        """Follow StockPilot's live events over its WebSocket, reconnecting as needed."""
        delay = 1.0
        while True:
            try:
                token = await self.sp.ensure_token()
                async with websockets.connect(self.sp.ws_url, open_timeout=10) as ws:
                    await ws.send(json.dumps({"type": "auth", "token": token}))
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "ready":
                            logger.info("Following StockPilot live events")
                            await self.hub.set_live(True)
                            delay = 1.0
                            self.wake.set()  # catch up on anything missed while offline
                        elif msg.get("type") == "analytics.updated":
                            if msg.get("module") == "inventory":
                                await self.hub.broadcast({"type": "catalogue"})
                            elif msg.get("module") == "delivery":
                                self.wake.set()
            except asyncio.CancelledError:
                raise
            except websockets.ConnectionClosed as e:
                if getattr(e.rcvd, "code", None) == 1008:
                    self.sp.token = None  # token rejected: sign in again
                logger.warning("StockPilot live connection closed; reconnecting")
            except Exception as e:
                logger.warning("StockPilot live connection failed (%s); retrying in %.0fs", e, delay)
            await self.hub.set_live(False)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def sync_loop(self) -> None:
        while True:
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=ORDER_POLL_SECONDS)
            except asyncio.TimeoutError:
                pass
            self.wake.clear()
            try:
                await self.sync_orders()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Order sync failed: %s", e)

    # ---- demo tools ----

    async def stock_shop(self) -> dict[str, Any]:
        """Add any starter fruit that's missing (as the shop owner would) and book the purchase."""
        existing = {r["name"] for r in await self.sp.call("GET", "/inventory/", params={"limit": 1000})}
        added = []
        for name, price, qty, shelf in STARTER_CATALOGUE:
            if name in existing:
                continue
            await self.sp.call("POST", "/inventory/", json={
                "name": name, "quantity": qty, "price": price, "status": "under_use",
                "expiry_date": (date.today() + timedelta(days=shelf)).isoformat(),
            })
            await self.sp.call("POST", "/accounts/", json={
                "amount": round(qty * price * COST_RATIO, 2), "transaction_type": "debit", "source_target": SUPPLIER,
                "category": "Fruit purchases", "remarks": f"Opening stock: {qty} × {name}",
            })
            added.append(name)
        return {"added": added}

    async def demo_shoppers(self, count: int) -> dict[str, Any]:
        placed = []
        for _ in range(count):
            fruits = [f for f in await self.catalogue() if f["available"] > 0]
            if not fruits:
                break
            name, phone, address = random.choice(DEMO_SHOPPERS)
            picks = random.sample(fruits, k=min(len(fruits), random.randint(1, 3)))
            items = [CartLine(item_id=f["id"], quantity=random.randint(1, min(3, f["available"]))) for f in picks]
            order = await self.place_order(CheckoutIn(
                name=name, phone=phone, address=address, items=items,
                slot=random.choice(list(SLOTS)), payment=random.choice(list(PAYMENTS)),
            ))
            placed.append(order["order_id"])
        return {"placed": placed}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


def create_app(stockpilot: StockPilot | None = None, data_dir: Path | None = None, background: bool = True) -> FastAPI:
    sp = stockpilot or StockPilot(API_URL, SHOP_USERNAME, SHOP_PASSWORD)
    shop = Shop(sp, OrderStore(data_dir or DATA_DIR), Hub())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = [asyncio.create_task(shop.realtime_loop()), asyncio.create_task(shop.sync_loop())] if background else []
        yield
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await sp.close()

    app = FastAPI(title=f"{SHOP_NAME} online shop", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.shop = shop

    def guarded(e: StockPilotError) -> HTTPException:
        if e.status in (400, 404, 409):
            return HTTPException(e.status, e.detail)
        if e.status == 403:
            return HTTPException(503, f"The shop's StockPilot account lacks a permission: {e.detail}")
        return HTTPException(503, e.detail)

    @app.get("/api/config")
    async def config():
        return {"shop_name": SHOP_NAME, "stockpilot_url": WEB_URL, "demo_tools": DEMO_TOOLS,
                "live": shop.hub.stockpilot_live, "slots": SLOTS, "payments": PAYMENTS}

    @app.get("/api/catalogue")
    async def catalogue():
        try:
            return await shop.catalogue()
        except StockPilotError as e:
            raise guarded(e)

    @app.post("/api/orders", status_code=201)
    async def place_order(data: CheckoutIn):
        try:
            return await shop.place_order(data)
        except StockPilotError as e:
            raise guarded(e)

    @app.get("/api/orders/{order_id}")
    async def track(order_id: str):
        try:
            return await shop.track(order_id)
        except StockPilotError as e:
            raise guarded(e)

    @app.post("/api/orders/{order_id}/cancel")
    async def cancel(order_id: str):
        try:
            return await shop.cancel(order_id)
        except StockPilotError as e:
            raise guarded(e)

    @app.post("/api/demo/stock-shop")
    async def demo_stock():
        if not DEMO_TOOLS:
            raise HTTPException(404)
        try:
            return await shop.stock_shop()
        except StockPilotError as e:
            raise guarded(e)

    @app.post("/api/demo/shoppers")
    async def demo_shoppers(count: int = 5):
        if not DEMO_TOOLS:
            raise HTTPException(404)
        try:
            return await shop.demo_shoppers(max(1, min(count, 20)))
        except StockPilotError as e:
            raise guarded(e)

    @app.websocket("/ws")
    async def live(ws: WebSocket):
        await ws.accept()
        shop.hub.clients[ws] = set()
        await ws.send_json({"type": "live", "connected": shop.hub.stockpilot_live})
        try:
            while True:
                msg = await ws.receive_json()
                if msg.get("type") == "watch":
                    shop.hub.clients[ws] = {str(o) for o in msg.get("orders", [])[:50]}
        except (WebSocketDisconnect, ValueError):
            pass
        finally:
            shop.hub.clients.pop(ws, None)

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "stockpilot_live": shop.hub.stockpilot_live}

    @app.get("/")
    async def index():
        return FileResponse(HERE / "static" / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    return app


app = create_app()
