"""
FreshBasket Fruits: a fruit shop's point-of-sale app built on StockPilot.

A separate client business that only talks to the StockPilot REST API: it never
touches PostgreSQL, the analytics outbox or WebSockets. Everything it does
(sales, deliveries, restocking, spoilage, expenses) shows up live on the
StockPilot dashboards, so it doubles as the end-to-end test client.

    streamlit run client_app/app.py          # or: docker compose --profile simulator up -d
"""

from __future__ import annotations

import os
import random
import string
import time
from datetime import date, datetime, timedelta
from typing import Any

import requests
import streamlit as st

SHOP_NAME = os.getenv("SHOP_NAME", "FreshBasket Fruits")
DEFAULT_BACKEND_URL = os.getenv("STOCKPILOT_API_URL", "http://127.0.0.1:8000")
DASHBOARD_URL = os.getenv("STOCKPILOT_WEB_URL", "http://localhost:8080")

st.set_page_config(page_title=SHOP_NAME, page_icon="🍎", layout="wide")


# ============================================================
# Shop data
# ============================================================

# Starter catalogue: (inventory name, selling price per unit, opening stock, shelf life in days).
# The unit is part of the name so the counter staff and the dashboards agree on it.
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

# Suppliers buy at roughly this share of the selling price.
COST_RATIO = 0.65
LOW_STOCK = 10

SUPPLIERS = ["Azadpur Mandi Traders", "Green Valley Orchards", "Konkan Mango Co.", "Daily Fresh Wholesale"]
CUSTOMERS = [
    "Priya Sharma", "Rahul Verma", "Ananya Iyer", "Mohammed Khan", "Sneha Patil", "Arjun Reddy",
    "Kavya Nair", "Vikram Singh", "Neha Gupta", "Rohan Das", "Fatima Shaikh", "Siddharth Rao",
]
PAYMENT_METHODS = ["Cash", "UPI", "Card"]
EXPENSE_CATEGORIES = ["Rent", "Electricity", "Staff wages", "Transport", "Packaging", "Other"]

# Delivery status → button label shown to shop staff.
NEXT_STEP_LABELS = {
    "packed": "📦 Packed",
    "out_for_delivery": "🛵 Send out",
    "delivered": "✅ Delivered & paid",
    "failed": "⚠️ Delivery failed",
    "pending": "↩️ Back to pending",
    "cancelled": "✖ Cancel",
}
STATUS_LABELS = {
    "pending": "🕒 New",
    "packed": "📦 Packed",
    "out_for_delivery": "🛵 Out for delivery",
    "delivered": "✅ Delivered",
    "failed": "⚠️ Failed",
    "cancelled": "✖ Cancelled",
}


# ============================================================
# Session state
# ============================================================

DEFAULT_STATE = {
    "token": None,
    "user": None,
    "activity": [],
    "bill_no": 0,  # part of the quantity widgets' keys: a new number gives a fresh, empty bill
    "flash": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# REST client
# ============================================================

def backend_url() -> str:
    return st.session_state.get("backend_url", DEFAULT_BACKEND_URL).rstrip("/")


def api(
    method: str,
    endpoint: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    operation: str = "API request",
) -> tuple[bool, Any]:
    """Every call to StockPilot goes through here and is recorded in the API log tab."""
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    try:
        response = requests.request(
            method, f"{backend_url()}{endpoint}", headers=headers, json=json_body, params=params, timeout=20
        )
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        status: int | str = response.status_code
        ok = response.ok
    except requests.RequestException as exc:
        payload, status, ok = f"{type(exc).__name__}: {exc}", "ERROR", False

    st.session_state.activity.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "operation": operation,
        "method": method,
        "endpoint": endpoint,
        "status": status,
        "detail": payload,
    })
    del st.session_state.activity[200:]
    return ok, payload


def error_text(payload: Any) -> str:
    if isinstance(payload, dict) and "detail" in payload:
        detail = payload["detail"]
        if isinstance(detail, list):  # FastAPI validation errors
            return "; ".join(str(d.get("msg", d)) for d in detail)
        return str(detail)
    return str(payload)


def flash(kind: str, message: str) -> None:
    """Show a message after the next rerun."""
    st.session_state.flash = (kind, message)


def rupees(amount: float) -> str:
    return f"₹{amount:,.0f}" if float(amount).is_integer() else f"₹{amount:,.2f}"


def short_code(length: int = 4) -> str:
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def new_order_id() -> str:
    return f"FB-{date.today():%y%m%d}-{short_code()}"


def fetch_stock() -> list[dict[str, Any]]:
    ok, payload = api("GET", "/inventory/", params={"limit": 500}, operation="Load stock")
    return sorted(payload, key=lambda i: i["name"]) if ok else []


def days_left(item: dict[str, Any]) -> int | None:
    if not item.get("expiry_date"):
        return None
    return (date.fromisoformat(item["expiry_date"]) - date.today()).days


# ============================================================
# Shop operations (each is a short sequence of REST calls)
# ============================================================

def move_stock(item: dict[str, Any], action: str, quantity: int, note: str) -> tuple[bool, Any]:
    return api(
        "PUT", f"/inventory/{item['id']}",
        json_body={"quantity": quantity, "action": action, "note": note},
        operation=f"Stock {action}: {item['name']}",
    )


def record_money(kind: str, amount: float, party: str, category: str, remarks: str) -> tuple[bool, Any]:
    return api(
        "POST", "/accounts/",
        json_body={
            "amount": round(amount, 2), "transaction_type": kind,
            "source_target": party[:200], "category": category, "remarks": remarks[:1000],
        },
        operation=f"Record {kind}: {category}",
    )


def set_order_status(order_id: str, status: str, remark: str) -> tuple[bool, Any]:
    return api(
        "PUT", f"/delivery/{order_id}/status",
        json_body={"status": status, "remark": remark},
        operation=f"Order {order_id} → {status}",
    )


def order_total(order_id: str) -> float:
    ok, items = api("GET", f"/delivery/{order_id}/items", operation=f"Order {order_id} items")
    return sum(i["quantity"] * i["unit_price"] for i in items) if ok else 0.0


def place_order(
    customer: str, phone: str, lines: list[tuple[dict[str, Any], int]], home_delivery: bool, payment: str
) -> tuple[bool, str]:
    """
    Create the order in StockPilot's delivery module with every line linked to its stock item.
    Counter sales are completed at once (stock is deducted on dispatch) and paid immediately;
    home deliveries stay open and are paid when delivered.
    """
    order_id = new_order_id()
    customer_id = f"{customer} ({phone})" if phone else customer
    ok, payload = api(
        "POST", "/delivery/",
        json_body={
            "order_id": order_id,
            "customer_id": customer_id[:80],
            "items": [
                {"product_name": item["name"], "quantity": qty, "unit_price": item["price"], "inventory_item_id": item["id"]}
                for item, qty in lines
            ],
            "remarks": f"{'Home delivery' if home_delivery else 'Counter sale'}; payment: {payment}",
        },
        operation=f"Place order {order_id}",
    )
    if not ok:
        return False, f"Could not place the order: {error_text(payload)}"
    if home_delivery:
        return True, f"Order **{order_id}** booked for home delivery ({payment} on delivery)."

    for step in ("packed", "out_for_delivery", "delivered"):
        ok, payload = set_order_status(order_id, step, "Counter sale")
        if not ok:
            set_order_status(order_id, "cancelled", "Counter sale could not be completed")
            return False, f"Order {order_id} cancelled: {error_text(payload)}"

    total = sum(item["price"] * qty for item, qty in lines)
    record_money("credit", total, customer, "Fruit sales", f"Order {order_id}, paid by {payment}")
    return True, f"Sale **{order_id}** completed: {rupees(total)} received by {payment}."


def advance_order(order_id: str, customer: str, status: str) -> tuple[bool, str]:
    ok, payload = set_order_status(order_id, status, f"{SHOP_NAME}: {status.replace('_', ' ')}")
    if not ok:
        return False, error_text(payload)
    if status == "delivered":
        total = order_total(order_id)
        record_money("credit", total, customer, "Fruit sales", f"Order {order_id}, paid on delivery")
        return True, f"{order_id} delivered; {rupees(total)} collected."
    return True, f"{order_id}: {STATUS_LABELS[status]}"


def restock(item: dict[str, Any], quantity: int, unit_cost: float, supplier: str) -> tuple[bool, str]:
    ok, payload = move_stock(item, "add", quantity, f"Purchase from {supplier}")
    if not ok:
        return False, error_text(payload)
    cost = quantity * unit_cost
    record_money("debit", cost, supplier, "Fruit purchases", f"{quantity} × {item['name']} @ {rupees(unit_cost)}")
    return True, f"Added {quantity} × {item['name']} from {supplier} ({rupees(cost)})."


def load_starter_catalogue(existing: list[dict[str, Any]]) -> tuple[int, list[str]]:
    have = {i["name"] for i in existing}
    created, errors = 0, []
    for name, price, qty, shelf_life in STARTER_CATALOGUE:
        if name in have:
            continue
        ok, payload = api(
            "POST", "/inventory/",
            json_body={
                "name": name, "quantity": qty, "price": price, "status": "under_use",
                "expiry_date": (date.today() + timedelta(days=shelf_life)).isoformat(),
            },
            operation=f"Add {name} to catalogue",
        )
        if ok:
            created += 1
            record_money("debit", qty * price * COST_RATIO, random.choice(SUPPLIERS), "Fruit purchases",
                         f"Opening stock: {qty} × {name}")
        else:
            errors.append(f"{name}: {error_text(payload)}")
    return created, errors


# ============================================================
# Sidebar: connection and sign-in
# ============================================================

st.sidebar.title(f"🍎 {SHOP_NAME}")
st.sidebar.caption("Point of sale · powered by StockPilot")

with st.sidebar.expander("StockPilot connection", expanded=not st.session_state.token):
    st.session_state.backend_url = st.text_input(
        "API URL", value=backend_url(), help="The StockPilot API (FastAPI). In Docker: http://api:8000"
    ).rstrip("/")
    st.markdown(f"[Open the StockPilot dashboard ↗]({DASHBOARD_URL})")

if st.session_state.token:
    user = st.session_state.user or {}
    st.sidebar.success(f"Signed in as **{user.get('username', '?')}**")
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state.token = st.session_state.user = None
        st.session_state.bill_no += 1
        st.rerun()


# ============================================================
# Sign-in screen
# ============================================================

if not st.session_state.token:
    st.title(f"🍎 {SHOP_NAME}")
    st.write(
        "Sign in with a **StockPilot account**. The shop needs the inventory, delivery and "
        "accounts permissions (an admin can grant them on *Users & Roles* in StockPilot)."
    )
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in", type="primary", use_container_width=True):
            ok, payload = api("POST", "/auth/login", json_body={"username": username, "password": password},
                              operation="Sign in")
            if ok and payload.get("access_token"):
                st.session_state.token = payload["access_token"]
                me_ok, me = api("GET", "/auth/me", operation="Load signed-in user")
                st.session_state.user = me if me_ok else {"username": username}
                st.rerun()
            st.error(f"Sign-in failed: {error_text(payload)}")
    st.stop()


permissions = set((st.session_state.user or {}).get("permissions", []))
missing = {"inventory.write", "delivery.write", "accounts.write"} - permissions
if missing:
    st.warning(
        f"Your account is missing {', '.join(sorted(missing))}. Some shop actions will be refused; "
        "ask a StockPilot admin to give you a role with these permissions."
    )

if st.session_state.flash:
    kind, message = st.session_state.flash
    getattr(st, kind)(message)
    st.session_state.flash = None


# ============================================================
# Pages
# ============================================================

# Sidebar navigation rather than st.tabs: tabs jump back to the first one on every rerun.
COUNTER, ORDERS, STOCK, CASH, RUSH, LOG = "🛒 Counter", "🛵 Orders", "🧺 Stock", "💰 Cash book", "⚡ Busy day", "🧪 API log"
page = st.sidebar.radio("Go to", [COUNTER, ORDERS, STOCK, CASH, RUSH, LOG], key="page")
st.title(page)

stock = fetch_stock() if page in (COUNTER, STOCK, RUSH) else []
on_shelf = [i for i in stock if i["quantity"] > 0]


# ------------------------------------------------------------
# Counter: sell from the shelf
# ------------------------------------------------------------

if page == COUNTER:
    if not stock:
        st.info("The shop has no products yet. Load the starter catalogue of 12 fruits to begin.")
        if st.button("🍉 Load starter catalogue", type="primary"):
            created, errors = load_starter_catalogue(stock)
            flash("error" if errors else "success",
                  f"Added {created} fruits." + ("".join(f"\n- {e}" for e in errors)))
            st.rerun()

    elif not on_shelf:
        st.warning("Everything is sold out. Restock on the **Stock** tab.")

    else:
        shelf_col, cart_col = st.columns([3, 2], gap="large")

        with shelf_col:
            st.subheader("On the shelf")
            cards = st.columns(3)
            lines = []
            for index, item in enumerate(on_shelf):
                left = days_left(item)
                with cards[index % 3].container(border=True):
                    st.markdown(f"**{item['name']}**")
                    st.markdown(f"{rupees(item['price'])} · {item['quantity']} in stock")
                    if left is not None and left <= 2:
                        st.caption(f"🔴 expires {'today' if left <= 0 else f'in {left}d'}")
                    elif item["quantity"] <= LOW_STOCK:
                        st.caption("🟠 running low")
                    else:
                        st.caption("🟢 fresh")
                    key = f"qty_{st.session_state.bill_no}_{item['id']}"
                    if st.session_state.get(key, 0) > item["quantity"]:  # stock fell since it was typed
                        st.session_state[key] = item["quantity"]
                    qty = st.number_input("Qty", min_value=0, max_value=item["quantity"], key=key,
                                          label_visibility="collapsed")
                    if qty:
                        lines.append((item, qty))

        with cart_col:
            st.subheader("Bill")
            if not lines:
                st.caption("Set quantities on the left to add fruit to the bill.")
            else:
                st.dataframe(
                    [{"Fruit": it["name"], "Qty": q, "Rate": rupees(it["price"]), "Amount": rupees(it["price"] * q)}
                     for it, q in lines],
                    hide_index=True, use_container_width=True,
                )
                st.metric("Total", rupees(sum(it["price"] * q for it, q in lines)))

            with st.form("checkout", clear_on_submit=True):
                customer = st.text_input("Customer name", value="Walk-in customer")
                phone = st.text_input("Phone (optional)")
                home_delivery = st.toggle("Home delivery")
                payment = st.radio("Payment", PAYMENT_METHODS, horizontal=True)
                submitted = st.form_submit_button("Place order", type="primary", use_container_width=True,
                                                  disabled=not lines)
            if submitted and lines:
                ok, message = place_order(customer.strip() or "Walk-in customer", phone.strip(), lines,
                                          home_delivery, payment)
                if ok:
                    st.session_state.bill_no += 1
                flash("success" if ok else "error", message)
                st.rerun()


# ------------------------------------------------------------
# Orders: home deliveries in progress
# ------------------------------------------------------------

if page == ORDERS:
    ok, active = api("GET", "/delivery/active", params={"limit": 100}, operation="Load open orders")
    active = active if ok else []
    st.subheader(f"Open orders ({len(active)})")
    if not active:
        st.caption("No home deliveries in progress. Turn on *Home delivery* at the counter to book one.")
    for order in active:
        with st.container(border=True):
            info_col, action_col = st.columns([3, 2])
            with info_col:
                st.markdown(f"**{order['order_id']}** · {order['customer_id']}")
                st.caption(f"{STATUS_LABELS.get(order['status'], order['status'])} · "
                           f"{order['items_count']} item(s) · booked {order['created_at'][:16].replace('T', ' ')}")
            with action_col:
                buttons = st.columns(max(len(order["allowed_next"]), 1))
                for col, nxt in zip(buttons, order["allowed_next"]):
                    if col.button(NEXT_STEP_LABELS.get(nxt, nxt), key=f"{order['order_id']}_{nxt}",
                                  use_container_width=True):
                        customer = order["customer_id"].split(" (")[0]
                        done, message = advance_order(order["order_id"], customer, nxt)
                        flash("success" if done else "error", message)
                        st.rerun()

    ok, finished = api("GET", "/delivery/finished", params={"limit": 20}, operation="Load finished orders")
    if ok and finished:
        st.subheader("Recently completed")
        st.dataframe(
            [{"Order": o["order_id"], "Customer": o["customer_id"], "Result": STATUS_LABELS.get(o["status"], o["status"]),
              "Items": o["items_count"], "Finished": (o.get("completed_at") or "")[:16].replace("T", " ")}
             for o in finished],
            hide_index=True, use_container_width=True,
        )


# ------------------------------------------------------------
# Stock: restock, spoilage, new products
# ------------------------------------------------------------

if page == STOCK:
    if stock:
        st.dataframe(
            [{"Fruit": i["name"], "In stock": i["quantity"], "Price": rupees(i["price"]),
              "Expires": i.get("expiry_date") or "—",
              "Days left": days_left(i) if days_left(i) is not None else "—",
              "Alert": ("Expired" if (days_left(i) or 1) <= 0 and i.get("expiry_date") else
                        "Sold out" if i["quantity"] == 0 else "Low" if i["quantity"] <= LOW_STOCK else "")}
             for i in stock],
            hide_index=True, use_container_width=True,
        )
        names = {i["name"]: i for i in stock}
        restock_col, waste_col = st.columns(2, gap="large")

        with restock_col:
            st.subheader("Receive from supplier")
            # Not a form: the suggested cost has to follow the chosen fruit.
            fruit = st.selectbox("Fruit", list(names), key="restock_fruit")
            quantity = st.number_input("Quantity received", min_value=1, value=20, key="restock_qty")
            unit_cost = st.number_input("Cost per unit (₹)", min_value=0.0, step=5.0, key=f"restock_cost_{fruit}",
                                        value=float(round(names[fruit]["price"] * COST_RATIO)))
            supplier = st.selectbox("Supplier", SUPPLIERS, key="restock_supplier")
            if st.button("Add to stock", type="primary", use_container_width=True):
                ok, message = restock(names[fruit], int(quantity), unit_cost, supplier)
                flash("success" if ok else "error", message)
                st.rerun()

        with waste_col:
            st.subheader("Write off spoilage")
            with st.form("spoilage", clear_on_submit=True):
                fruit = st.selectbox("Fruit", [n for n, i in names.items() if i["quantity"] > 0] or list(names))
                quantity = st.number_input("Quantity spoiled", min_value=1, value=2)
                reason = st.selectbox("Reason", ["Overripe", "Bruised", "Expired", "Damaged in transit"])
                if st.form_submit_button("Write off", use_container_width=True):
                    ok, payload = move_stock(names[fruit], "consume", int(quantity), f"Spoilage: {reason}")
                    flash("success" if ok else "error",
                          f"Wrote off {quantity} × {fruit}." if ok else error_text(payload))
                    st.rerun()

    st.subheader("Add a new fruit")
    with st.form("new_fruit", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Name with unit", placeholder="Dragon Fruit (piece)")
        price = c2.number_input("Selling price (₹)", min_value=0.0, value=100.0, step=5.0)
        quantity = c3.number_input("Opening stock", min_value=0, value=20)
        shelf_life = c4.number_input("Shelf life (days)", min_value=1, value=7)
        if st.form_submit_button("Add fruit", use_container_width=True) and name.strip():
            ok, payload = api(
                "POST", "/inventory/",
                json_body={"name": name.strip(), "quantity": int(quantity), "price": price, "status": "under_use",
                           "expiry_date": (date.today() + timedelta(days=int(shelf_life))).isoformat()},
                operation=f"Add {name.strip()} to catalogue",
            )
            flash("success" if ok else "error", f"Added {name.strip()}." if ok else error_text(payload))
            st.rerun()

    if stock and len(stock) < len(STARTER_CATALOGUE) and st.button("🍉 Add missing starter fruits"):
        created, errors = load_starter_catalogue(stock)
        flash("error" if errors else "success", f"Added {created} fruits." + "".join(f"\n- {e}" for e in errors))
        st.rerun()


# ------------------------------------------------------------
# Cash book: money in and out
# ------------------------------------------------------------

if page == CASH:
    ok, summary = api("GET", "/accounts/summary", operation="Load cash summary")
    if ok:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Balance", rupees(summary["current_balance"]))
        m2.metric("Money in", rupees(summary["total_credit"]))
        m3.metric("Money out", rupees(summary["total_debit"]))
        m4.metric("Last 30 days", rupees(summary["last_30_days_net"]))

    book_col, expense_col = st.columns([3, 2], gap="large")
    with book_col:
        st.subheader("Recent entries")
        ok, entries = api("GET", "/accounts/", params={"limit": 25}, operation="Load cash book")
        if ok and entries:
            st.dataframe(
                [{"When": e["date"][:16].replace("T", " "), "In / Out": "In" if e["transaction_type"] == "credit" else "Out",
                  "Amount": rupees(e["amount"]), "Party": e["source_target"], "Category": e["category"],
                  "Note": e.get("remarks") or ""}
                 for e in entries],
                hide_index=True, use_container_width=True,
            )
        else:
            st.caption("No entries yet.")
    with expense_col:
        st.subheader("Pay an expense")
        with st.form("expense", clear_on_submit=True):
            category = st.selectbox("Category", EXPENSE_CATEGORIES)
            amount = st.number_input("Amount (₹)", min_value=1.0, value=500.0, step=50.0)
            paid_to = st.text_input("Paid to", value="")
            note = st.text_input("Note", value="")
            if st.form_submit_button("Record expense", type="primary", use_container_width=True):
                ok, payload = record_money("debit", amount, paid_to or category, category, note or category)
                flash("success" if ok else "error",
                      f"Recorded {rupees(amount)} for {category}." if ok else error_text(payload))
                st.rerun()


# ------------------------------------------------------------
# Busy day: generate realistic shop traffic
# ------------------------------------------------------------

if page == RUSH:
    st.markdown(
        "Simulate a stretch of trading: customers buy at the counter and order home deliveries, riders "
        "deliver (some fail), the shop restocks what runs low and writes off spoiled fruit. "
        f"Keep the [StockPilot dashboard]({DASHBOARD_URL}) open to watch it update live."
    )
    c1, c2, c3 = st.columns(3)
    customers = c1.slider("Customers", 5, 100, 20)
    delivery_share = c2.slider("Home delivery share", 0.0, 1.0, 0.3)
    pause = c3.slider("Pause between customers (s)", 0.0, 3.0, 0.5)

    if st.button("Open the shop", type="primary", disabled=not on_shelf):
        progress = st.progress(0.0)
        log = st.container(height=320)
        tally = {"sales": 0, "orders": 0, "delivered": 0, "failed": 0, "restocks": 0, "spoilage": 0, "errors": 0}
        open_orders: list[tuple[str, str]] = []

        for n in range(customers):
            shelf = [i for i in fetch_stock() if i["quantity"] > 0]
            customer = random.choice(CUSTOMERS)

            if shelf:
                picks = random.sample(shelf, k=min(len(shelf), random.randint(1, 3)))
                lines = [(i, random.randint(1, max(1, min(5, i["quantity"] // 2)))) for i in picks]
                home = random.random() < delivery_share
                ok, message = place_order(customer, f"98{random.randint(10000000, 99999999)}", lines, home,
                                          random.choice(PAYMENT_METHODS))
                log.write(("✅ " if ok else "❌ ") + message)
                if ok and home:
                    tally["orders"] += 1
                    open_orders.append((message.split("**")[1], customer))
                elif ok:
                    tally["sales"] += 1
                else:
                    tally["errors"] += 1

            # Riders move earlier orders along.
            if open_orders and random.random() < 0.5:
                order_id, who = open_orders.pop(0)
                for step in ("packed", "out_for_delivery"):
                    advance_order(order_id, who, step)
                outcome = "failed" if random.random() < 0.1 else "delivered"
                ok, message = advance_order(order_id, who, outcome)
                tally[outcome] += ok
                log.write(("🛵 " if outcome == "delivered" else "⚠️ ") + message)

            # Restock anything running low, now and then.
            if random.random() < 0.25:
                low = [i for i in fetch_stock() if i["quantity"] <= LOW_STOCK]
                if low:
                    item = random.choice(low)
                    ok, message = restock(item, random.randint(20, 40), round(item["price"] * COST_RATIO),
                                          random.choice(SUPPLIERS))
                    tally["restocks"] += ok
                    log.write("🚚 " + message)

            # A little fruit always spoils.
            if shelf and random.random() < 0.1:
                item = random.choice(shelf)
                if move_stock(item, "consume", 1, "Spoilage: overripe")[0]:
                    tally["spoilage"] += 1
                    log.write(f"🗑️ Wrote off 1 × {item['name']}")

            progress.progress((n + 1) / customers, text=f"Customer {n + 1} of {customers}")
            time.sleep(pause)

        # Close the day: deliver whatever is still open.
        for order_id, who in open_orders:
            for step in ("packed", "out_for_delivery", "delivered"):
                ok, message = advance_order(order_id, who, step)
            tally["delivered"] += ok
        st.success(
            f"Day closed: {tally['sales']} counter sales, {tally['orders']} home orders "
            f"({tally['delivered']} delivered, {tally['failed']} failed), {tally['restocks']} restocks, "
            f"{tally['spoilage']} write-offs, {tally['errors']} errors."
        )


# ------------------------------------------------------------
# API log: every REST call this client made (for testing)
# ------------------------------------------------------------

if page == LOG:
    st.caption(f"Every call to the StockPilot API at `{backend_url()}`, newest first.")
    if st.button("Clear log"):
        st.session_state.activity = []
        st.rerun()
    for entry in st.session_state.activity:
        status = entry["status"]
        icon = "🟢" if isinstance(status, int) and 200 <= status < 300 else "🔴"
        with st.expander(f"{icon} {entry['time']} {entry['method']} {entry['endpoint']} → {status} · {entry['operation']}"):
            detail = entry["detail"]
            if isinstance(detail, (dict, list)):
                st.json(detail)
            else:
                st.code(str(detail))
