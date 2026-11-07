# Backend

FastAPI app in `backend/`, Python 3.12. Entry point: `backend/main.py`. Interactive API docs
(Swagger) are at `http://localhost:8000/docs` when the stack runs locally.

## Code layout

```
backend/
  main.py                 app, middleware, router registration, /health, start-up seeding
  core/
    config.py             every setting (env vars) in one Settings class
    time.py               utcnow()/utctoday() helpers (all times are UTC)
    pagination.py         limit/offset + X-Total-Count header
    mail.py               SMTP sender for reset emails (optional)
    auth/                 register, login, JWT, bcrypt, password change and reset
    rbac/                 permission catalogue, roles, users, seeding, require_permission()
    realtime/             LISTEN thread → ConnectionManager → WebSocket /ws/realtime
    analytics/stats.py    median, MAD, modified z-scores, histograms
    database/             engine/session, get_db dependency, model registry
  modules/
    inventory/ delivery/ accounts/ organization/ projects/   business modules (see below)
    business/             company profile and GSTIN/PAN/CIN verification
    ai/                   Ollama client, read-only tools, assistant
  outbox/                 outbox model and queue operations
  workers/
    analytics_worker.py   LISTEN + batch processing loop
    dispatcher.py         event → handle_<event_type>() in modules/<module>/analytics.py
    rebuild.py            recompute all projections from source tables
  scripts/create_admin.py create or promote an admin from the command line
  alembic/                migrations (see DATABASE.md)
```

Each business module has the same layers: `domain/` (pure rules), `application/` (services and
DTOs), `infrastructure/` (models, repository, projections), `facade.py`, `router.py`,
`analytics.py` and `analytics_router.py`. [ARCHITECTURE.md](ARCHITECTURE.md) explains how they fit
together.

### Conventions

- **Validation:** routers stay thin. Pydantic DTOs validate input: types, lengths, positive
  amounts.
- **Domain errors:** domain code raises plain exceptions (`InventoryError`,
  `InvalidTransition`, `CycleError`). Routers map them to HTTP codes: 400 for a broken rule, 404
  if not found, 409 for a conflict such as a duplicate name or a wrong status.
- **Transactions:** services own the transaction. Facade methods used by other modules don't
  commit, so the caller's transaction covers everything.
- **Lists:** list endpoints take `limit`/`offset` and return the total in the `X-Total-Count`
  header.
- **Times:** timestamps are stored and returned in UTC (ISO 8601). The delivery analytics
  endpoint accepts `tz_offset_minutes`, so its hour-of-day histogram matches the user's clock.

## Business modules and rules

### Inventory (`modules/inventory`)

- **Items:** name (unique), quantity, on-order quantity, price, status and expiry date.
- **Stock movements:** `PUT /inventory/{id}` with an `action`. The arithmetic lives in
  `domain/entities.py:apply_movement`:

| Action | Effect |
|---|---|
| `add` | stock + n; first reduces the on-order quantity (goods received) |
| `consume`, `deliver` | stock − n; fails with 400 if not enough is in stock; status becomes `consumed` at 0 |
| `return` | stock + n |
| `order` | on-order + n (purchase order placed) |

- **Logging and locking:** every movement writes an `inventory_logs` row and locks the item row.
- **Analytics:**
  - Consumption series and monthly orders.
  - **Alerts:** low stock, near expiry (stock that won't be used up before it expires), and
    dead stock (no movement for N days).
  - **Reorder suggestions:** `rate × coverage_days − (stock + on_order)`.
  - **Stock-out forecast:** `stock ÷ average daily consumption`.
  - **Consumption anomalies:** see the statistics section below.

### Delivery (`modules/delivery`)

The status workflow lives in `domain/entities.py:TRANSITIONS`:

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> packed
    pending --> cancelled
    packed --> pending
    packed --> out_for_delivery
    packed --> cancelled
    out_for_delivery --> delivered
    out_for_delivery --> failed
    failed --> pending : retry
    failed --> cancelled
    delivered --> [*]
    cancelled --> [*]
```

- **Linking items to stock:** an item can name an `inventory_item_id`. When it doesn't, the
  service matches the product name to an inventory item.
- **Moving to `out_for_delivery`:** deducts the linked stock, in the same transaction as the
  status change. Rows are locked in id order, which avoids deadlocks. If there isn't enough
  stock, the whole change is refused.
- **Moving to `failed` or `cancelled` after dispatch:** returns the stock. `stock_deducted` stops
  it being returned twice.
- **Status history:** every change is logged in `delivery_logs`, with an optional remark.
- **Analytics:** deliveries per day with a moving average, most-ordered products, the status
  mix, and a peak-hour histogram.

### Accounts (`modules/accounts`)

- **Ledger:** `credit` (income) and `debit` (expense) transactions, each with a counterparty
  (`source_target`), a category and remarks.
- **`GET /accounts/summary`:** the balance and the last 30 days' net.
- **Analytics:** income against expenses over time, a category breakdown, top customers and
  suppliers, and anomalies.
- **Liquidity score (0–100):** up to 60 points for net cash flow relative to spending
  (`30 + 30·tanh(net ÷ debits)`), plus up to 40 points for runway. Runway is the number of days
  the balance covers average spending; it earns full points at 60 days.

### Organization (`modules/organization`)

- Employees have a business ID, name, role, salary, manager and departments.
- `domain/entities.py:would_create_cycle` refuses a manager change that would create a reporting
  loop (A → B → A).
- Analytics: headcount per department, a salary histogram and the reporting tree for the org
  chart.

### Projects (`modules/projects`)

- **Data:** projects have tasks, dependencies, three-point estimates (optimistic, most likely,
  pessimistic) and assigned employees.
- **Scheduling** (`domain/scheduling.py`):
  - PERT expected duration `(o + 4m + p) / 6`, and standard deviation `(p − o) / 6`.
  - Topological sort, which rejects dependency loops with 400.
  - The critical path method: a forward pass (ES/EF), a backward pass (LS/LF) and float. Tasks
    with zero float form the critical path.
  - Resource conflicts: one employee on two tasks whose planned intervals overlap.
- **`POST /projects/{id}/simulate`:** returns the schedule, the critical path, the project's
  standard deviation, conflicts and the days left before the deadline.
- **Analytics:** a portfolio overview with schedule risk, and a snapshot for each project.

### Business profile (`modules/business`)

Registration numbers are checked offline in `domain/registration.py`:
- **GSTIN:** 15 characters, a valid state code, and the mod-36 checksum. It must embed the PAN.
- **PAN:** format, and the holder type from the 4th letter (company, firm, individual…).
- **CIN:** structure, year of incorporation and company class.
- **Cross-checks:** the GSTIN state, the declared state and the CIN state must agree. A company's
  CIN must go with a company PAN, and the PAN's 5th letter must match the legal name.

A profile that passes is *awaiting review*. An admin with `business.manage` approves or rejects
it. Editing a registration field resets the review.

## Statistics used for anomalies (`core/analytics/stats.py`)

Anomaly detection uses the **modified z-score** (Iglewicz and Hoaglin), which outliers can't
distort the way they distort a mean and standard deviation:

```
MAD = median(|xᵢ − median(x)|)
zᵢ  = 0.6745 · (xᵢ − median(x)) / MAD
flag when |zᵢ| > 3.5, needs at least 5 samples
```

If MAD is 0 (many identical values), it uses the mean absolute deviation instead
(`(xᵢ − median) / (1.2533 · mean |deviation|)`).
- Transactions are scored within their own category and type.
- Daily consumption is scored per item.

## Authentication and permissions

- **Registration:** `POST /auth/register` creates an active user with **no roles**. An admin then
  grants a role on *Users & Roles*. `ALLOW_REGISTRATION=false` turns sign-up off.
- **Login:** `POST /auth/login` returns `{access_token, token_type}`. Send the token as
  `Authorization: Bearer <token>`. `GET /auth/me` returns the user and their permission list.
- **Route guards:** `require_permission("inventory.write")` (`core/rbac/dependencies.py`) checks
  that the user is active and holds the permission. The `admin` role passes every check.
- **Catalogue:** `core/rbac/permissions.py`:

| Permission | Allows |
|---|---|
| `inventory.read` / `.write` | view / change items and stock (`read` also covers inventory analytics) |
| `delivery.read` / `.write` | view / create and update deliveries |
| `accounts.read` / `.write` | view / add and delete transactions |
| `organization.read` / `.write` | view / manage employees and departments |
| `projects.read` / `.write` | view and simulate / manage projects and tasks |
| `business.manage` | edit and review the business profile |
| `ai.use` | the AI assistant and the Summarize buttons |
| `rbac.manage` | manage roles and users, create reset links |

- **Seeding:** on start-up (`SEED_RBAC=true`), the API creates any missing permissions and moves
  roles off legacy permission names. It also creates `ADMIN_USERNAME` if all three `ADMIN_*`
  variables are set. You can do the same by hand with `python -m backend.scripts.create_admin`.
- **Passwords:**
  - **Change:** `POST /auth/change-password` raises `token_version` and returns a new token for
    the current session. This signs out every other session.
  - **Admin reset link:** `POST /rbac/users/{id}/reset-link` makes a single-use link.
  - **Forgot password:** `POST /auth/forgot-password` emails the link when SMTP is configured.
    It always returns 202 with the same message, so it never reveals whether an account exists.
  - **Using the link:** `POST /auth/reset-password` sets the new password.

## Realtime WebSocket

`ws://<host>/ws/realtime` (through nginx: `/api/ws/realtime`):

1. The client connects and sends `{"type":"auth","token":"<jwt>"}` within 10 seconds.
2. The server replies `{"type":"ready"}`, or closes with code 1008 if the token is invalid.
3. From then on the server pushes `{"type":"analytics.updated","module":"inventory","event_type":"stock_consumed",…}`,
   but only for modules the user can read.

## AI module (`modules/ai`)

- **`client.py`:** a small Ollama HTTP client (`/api/chat`, `/api/tags`). It raises
  `ToolsNotSupported` for models without tool calling.
- **`tools.py`:** read-only tools, each tied to a permission:
  - Inventory: `inventory_alerts`, `stockout_predictions`, `reorder_suggestions`,
    `search_inventory`, `inventory_anomalies`.
  - Accounts: `accounts_summary`, `transaction_anomalies`.
  - Delivery: `delivery_overview`, `active_deliveries`.
  - Organization: `organization_overview`, `search_employees`.
  - Projects: `projects_overview`, `project_schedule`.
  - Business: `business_profile`.
- **`assistant.py`:**
  - The chat loop runs up to 4 tool rounds. Each tool result is limited to 6,000 characters.
  - It falls back to context mode when the model lacks tool support or returns an empty answer.
  - `insights(module)` produces the Summarize briefing.
- **Endpoints:**
  - `GET /ai/status`: is AI enabled, can the API reach Ollama, is the model downloaded, and can
    this user use it.
  - `POST /ai/chat` with `{messages:[{role,content}]}`.
  - `POST /ai/insights` with `{module}`.

## API reference

All paths are relative to the API root (`http://localhost:8000`, or `/api` through nginx).
"Signed in" means any active user with a valid token.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/`, `/health` | none | liveness; `/health` also reports the database and realtime listener |
| POST | `/auth/register` | none (if enabled) | create an account |
| POST | `/auth/login` | none | get a JWT |
| GET | `/auth/me` | signed in | current user and permissions |
| GET | `/auth/options` | none | whether registration and email are enabled |
| POST | `/auth/change-password` | signed in | change own password |
| POST | `/auth/forgot-password`, `/auth/reset-password` | none | email reset / use a reset link |
| GET | `/rbac/permissions` | `rbac.manage` | permission catalogue |
| GET, POST | `/rbac/` | `rbac.manage` | list / create roles |
| PUT, DELETE | `/rbac/{role_name}` | `rbac.manage` | edit / delete a role |
| GET | `/rbac/users` | `rbac.manage` | list users |
| PUT | `/rbac/users/{id}/roles` | `rbac.manage` | set a user's roles |
| PATCH | `/rbac/users/{id}` | `rbac.manage` | activate / deactivate |
| POST | `/rbac/users/{id}/reset-link` | `rbac.manage` | one-time password reset link |
| GET | `/business/profile` | signed in | company profile and verification report |
| PUT | `/business/profile` | `business.manage` | save the profile (runs the checks) |
| POST | `/business/profile/review` | `business.manage` | approve or reject |
| POST | `/business/validate` | signed in | check numbers without saving |
| GET | `/business/states` | signed in | GST state codes |
| GET | `/ai/status` | signed in | AI availability |
| POST | `/ai/chat`, `/ai/insights` | `ai.use` | assistant / Summarize |
| GET, POST | `/inventory/` | read / write | list (filters, paging) / create item |
| GET, DELETE | `/inventory/{id}` | read / write | one item / delete |
| PUT | `/inventory/{id}` | write | stock movement `{action, quantity, note}` |
| PUT | `/inventory/{id}/status` | write | set status |
| GET | `/inventory/{id}/logs` | read | movement history |
| POST | `/delivery/` | write | create an order with items |
| GET | `/delivery/active`, `/delivery/finished` | read | open / closed orders |
| GET | `/delivery/{order_id}` | read | one order |
| GET | `/delivery/{order_id}/items`, `/logs` | read | items / status history |
| PUT | `/delivery/{order_id}/status` | write | move along the workflow `{status, remark}` |
| GET, POST | `/accounts/` | read / write | list / add a transaction |
| GET | `/accounts/summary` | read | balance and 30-day net |
| DELETE | `/accounts/{id}` | write | delete a transaction |
| GET, POST | `/organization/departments` | read / write | departments |
| DELETE | `/organization/departments/{name}` | write | delete a department |
| GET, POST | `/organization/employees` | read / write | search / add employees |
| PUT, DELETE | `/organization/employees/{employee_id}` | write | edit / remove |
| GET, POST | `/projects/` | read / write | list / create projects |
| GET, PUT, DELETE | `/projects/{id}` | read / write | one project |
| GET, POST | `/projects/{id}/tasks` | read / write | tasks |
| PUT, DELETE | `/projects/{id}/tasks/{task_id}` | write | edit / delete a task |
| POST | `/projects/{id}/simulate` | read | CPM/PERT schedule |
| GET | `/analytics/inventory/series`, `alerts`, `reorder-suggestions`, `stockout-predictions`, `anomalies` | `inventory.read` | inventory analytics |
| GET | `/analytics/accounts/overview`, `series`, `anomalies` | `accounts.read` | accounts analytics |
| GET | `/analytics/delivery/overview` | `delivery.read` | delivery analytics |
| GET | `/analytics/organization/overview` | `organization.read` | organization analytics |
| GET | `/analytics/projects/overview`, `projects`, `project/{id}` | `projects.read` | project analytics |
| WS | `/ws/realtime` | token in first message | live analytics events |

The request and response schemas for every endpoint are in Swagger at `/docs`.

## Workers and scripts

| Command | Purpose |
|---|---|
| `python -m backend.workers.analytics_worker` | the analytics worker (the `worker` container) |
| `python -m backend.workers.rebuild [inventory accounts …]` | rebuild projections; stop the worker first |
| `python -m backend.scripts.create_admin` | create or promote an admin interactively |

In Docker, prefix these with `docker compose exec api`.

## Configuration

Every setting is declared in `backend/core/config.py` and documented in `.env.example`.

| Group | Settings |
|---|---|
| Core | `APP_ENV`, `LOG_LEVEL`, `CORS_ORIGINS` |
| Database | `DATABASE_URL`, `DIRECT_DATABASE_URL`, `DB_ECHO` |
| Auth | `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALLOW_REGISTRATION`, `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SEED_RBAC` |
| Password reset | `APP_BASE_URL`, `PASSWORD_RESET_TTL_MINUTES`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` |
| Outbox and realtime | `OUTBOX_BATCH_SIZE`, `OUTBOX_POLL_TIMEOUT`, `OUTBOX_MAX_ATTEMPTS`, `OUTBOX_MAX_BACKOFF_SECONDS`, `OUTBOX_RETENTION_DAYS`, `STALE_LOCK_SECONDS`, `OUTBOX_LISTEN_CHANNEL`, `REALTIME_LISTEN_CHANNEL` |
| AI | `AI_ENABLED`, `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` |

## Running without Docker

Run these from the repository root with Python 3.12 or newer and a PostgreSQL database:

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; .venv/bin/activate elsewhere
pip install -r backend/requirements.txt
# .env: DATABASE_URL, JWT_SECRET, APP_ENV=development, ADMIN_*
alembic -c backend/alembic.ini upgrade head
uvicorn backend.main:app --reload                   # http://127.0.0.1:8000/docs
python -m backend.workers.analytics_worker          # second terminal
```

## Tests

```bash
pytest tests/unit                       # no database needed
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/stockpilot_test \
  pytest tests/integration              # WIPES and migrates that database
```

| Suite | Covers |
|---|---|
| `unit/test_domain_rules.py` | stock arithmetic, delivery transitions, reporting-loop detection |
| `unit/test_scheduling.py` | PERT, CPM, critical path, cycles, resource conflicts |
| `unit/test_analytics_math.py` | modified z-scores, histograms, transaction anomalies, liquidity score, reorder and stock-out maths, moving averages, time-zone hour shift |
| `unit/test_registration.py` | GSTIN checksum, PAN/CIN formats, cross-checks |
| `unit/test_core.py` | password hashing, JWT tampering, permission catalogue, admin role, outbox retry and dead-lettering, dispatcher, app start-up |
| `unit/test_ai_assistant.py` | tool loop, permission filtering, fallbacks, truncation (with a fake Ollama) |
| `integration/test_api_flows.py` | real HTTP calls against PostgreSQL: auth, stock, delivery with stock deduction and return, accounts, worker-built analytics |
| `integration/test_improvements.py` | editing projects and tasks, dependency loops, password change and reset flows |

CI (`.github/workflows/ci.yml`) runs on every push and pull request:
- both test suites against a PostgreSQL service,
- an offline render of the migrations,
- the frontend lint and build,
- a Docker image build and a smoke test of the composed stack.

## Adding a new module

1. Create `backend/modules/<name>/` with the `domain/`, `application/` and `infrastructure/`
   layers and a `router.py`.
2. Add `<name>.read` and `<name>.write` to `MODULES` in `core/rbac/permissions.py`.
3. Add the model module to `MODEL_MODULES` in `core/database/registry.py`.
4. Write an Alembic migration.
5. Include the router in `main.py`.
6. For live analytics:
   - emit outbox events from ORM hooks with `outbox.repository.emit_event`,
   - add `handle_<event_type>` functions in `analytics.py`,
   - add the module to `KNOWN_MODULES` in `workers/dispatcher.py` and to `MODULE_READ_PERMISSION`.
