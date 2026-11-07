# Client app: FreshBasket Fruits

`client_app/app.py` is a point-of-sale app for an imagined fruit shop, built with Streamlit. It
shows how an outside business would use StockPilot. It also serves as the end-to-end test client.

- It uses **only the public REST API**, the same calls documented in
  [BACKEND.md](BACKEND.md#api-reference). It never touches the database, the outbox or the
  WebSocket.
- Everything it does goes through the normal permission checks, business rules and analytics
  pipeline. The results appear live on the StockPilot dashboards.

## Run it

```bash
docker compose --profile simulator up -d --build      # http://localhost:8501
# or without Docker (the API must be running):
cd client_app && pip install -r requirements.txt && streamlit run app.py
```

| Variable | Default | Use |
|---|---|---|
| `STOCKPILOT_API_URL` | `http://127.0.0.1:8000` (Docker: `http://api:8000`) | API the shop calls; you can also change it on the sign-in screen |
| `STOCKPILOT_WEB_URL` | `http://localhost:8080` | link to the StockPilot dashboard in the sidebar |
| `SHOP_NAME` | `FreshBasket Fruits` | shop name shown in the app |

**First run:**
1. Sign in with a StockPilot account that can write inventory, delivery and accounts. The admin
   account works.
2. Click **Load starter catalogue**. This adds 12 fruits (price, opening stock and shelf life for
   each) and records the opening purchase as an expense.

The app warns if the account lacks a permission it needs.

## Pages

| Page | What the shop does | StockPilot calls |
|---|---|---|
| 🛒 **Counter** | builds a bill from the shelf, then takes payment (cash, UPI or card); optional home delivery | `POST /delivery/` with items linked by `inventory_item_id`. A counter sale moves straight to `packed → out_for_delivery → delivered` (stock is deducted on dispatch), then `POST /accounts/` adds a "Fruit sales" credit |
| 🛵 **Orders** | home deliveries: Pack, Send out, Delivered (paid) or Failed | `PUT /delivery/{id}/status`. *Delivered* records the payment. *Failed* returns the stock automatically |
| 🧺 **Stock** | stock levels with days to expiry; receive stock from a supplier; write off spoilage; add a new fruit | `PUT /inventory/{id}` (`add`, `consume`) + `POST /accounts/` debit for purchases; `POST /inventory/` |
| 💰 **Cash book** | balance, last 30 days, recent entries; record expenses (rent, electricity, staff wages, transport…) | `GET /accounts/summary`, `GET /accounts/`, `POST /accounts/` |
| ⚡ **Busy day** | simulates a day of customers: counter sales, deliveries (about 10% fail), restocking of low items, spoilage | all of the above, in a loop with a configurable pause |
| 🧪 **API log** | every request the app made, with method, path, status and time | none (local log) |

If any step of a counter sale fails (for example, not enough stock), the order is cancelled.
Partly completed orders are never left behind.

## Code structure

| Part | Functions |
|---|---|
| HTTP | `api()`: one wrapper for every call. Adds the token, records the call in the API log and returns `(ok, payload)`; `error_text()` turns API errors into readable text |
| Business actions | `place_order`, `advance_order`, `restock`, `move_stock`, `record_money`, `set_order_status`, `load_starter_catalogue` |
| Helpers | `fetch_stock`, `days_left`, `order_total`, `new_order_id` (`FB-YYMMDD-XXXX`), `rupees` |
| UI | a sidebar radio for navigation (Streamlit tabs reset on every rerun); a `bill_no` counter in widget keys clears the bill after each sale |

Theme: `client_app/.streamlit/config.toml` (light, green accent).

## Testing with it

1. Open StockPilot (http://localhost:8080) and the shop (http://localhost:8501) side by side.
2. Make a counter sale. On the StockPilot dashboard, stock and income update within about a
   second.
3. Run **Busy day** with 30–50 customers. This fills the analytics pages: consumption, cash flow,
   delivery hours, top products and anomalies. That data gives the AI assistant something real
   to answer from.
4. Check **API log** for any request that failed.
