# StockPilot Enterprise

A business operating system for small manufacturers and shops. One web app covers inventory,
deliveries, accounts, staff and projects. Its dashboards update live, a private AI assistant
answers questions about your own data, and Indian business registrations (GSTIN / PAN / CIN) are
checked offline.

```
 React (Vite) ──/api──▶ nginx ──▶ FastAPI ──▶ PostgreSQL
      ▲                               │  business rows + outbox events (same transaction)
      │ WebSocket                     ▼
      └──── realtime listener ◀── pg_notify ◀── analytics worker ──▶ projection tables
 FastAPI ──▶ Ollama (local LLM, optional) · FreshBasket shop app ──REST──▶ FastAPI
```

## Team

| Member | Roll no. | Role |
|---|---|---|
| Abiram Krishna | 24CSB1A02 | Frontend and client app |
| Aditya Madhu | 24CSB1A03 | Backend and documentation |
| Aditya Shrivastava | 24CSB1A04 | Database integration, system architecture, website and deployment |

## Features

| Module | What it does |
|---|---|
| Inventory | items, stock movements (receive / consume / deliver / order / return) with row locking, history, expiry dates |
| Delivery | orders with a status workflow; linked stock is deducted on dispatch and returned if the delivery fails or is cancelled |
| Accounts | credit/debit ledger, balance and 30-day net |
| Organization | employees, departments, a loop-proof reporting hierarchy, org chart |
| Projects | tasks with dependencies, CPM/PERT critical path, slack and resource-conflict detection |
| Analytics | live dashboards per module, reorder suggestions, stock-out forecast, liquidity score, schedule risk |
| Anomaly detection | unusual transactions and consumption spikes (robust median/MAD statistics) |
| AI assistant and insights | chat with your data, plus a **Summarize** button on every analytics page; read-only and permission-scoped; runs locally on Ollama |
| Business profile | GSTIN checksum, PAN/CIN format and cross-checks, then admin approval |
| Users and roles | role-based access (`module.read` / `module.write`), user activation, admin bootstrap |
| Passwords | change password, one-time admin reset links, optional "forgot password" emails |
| Backups | daily automatic database dumps with retention and one-command restore |
| FreshBasket Fruits | a demo fruit-shop app that runs entirely on the StockPilot API and drives realistic traffic |

## Quick start (Docker)

Requirements: Docker Desktop (Windows/macOS) or Docker Engine with Compose v2 (Linux). About
4 GB of free RAM, or 8 GB with the AI assistant.

```bash
git clone https://github.com/a-code-sri/StockPilot-Enterprise.git
cd StockPilot-Enterprise
cp .env.example .env        # PowerShell: copy .env.example .env
# Edit .env: set POSTGRES_PASSWORD, JWT_SECRET (32+ chars) and ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build
```

Open **http://localhost:8080** and sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
Swagger, the API's interactive docs, is at http://localhost:8000/docs, reachable from this
computer only.

| Add-on | Command | Details |
|---|---|---|
| AI assistant | `docker compose --profile ai up -d` (first run downloads ~2 GB) | [docs/AI_SETUP.md](docs/AI_SETUP.md) |
| FreshBasket shop | `docker compose --profile simulator up -d --build` → http://localhost:8501 | [docs/CLIENT_APP.md](docs/CLIENT_APP.md) |
| Public HTTPS | `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile ai up -d --build` | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

To enable several profiles at once, list them in `.env`, for example `COMPOSE_PROFILES=ai,simulator`.
Stop with `docker compose down`. Adding `-v` also **deletes the database**.

## Documentation

| Guide | Contents |
|---|---|
| [User guide](docs/USER_GUIDE.md) | using each page of the app |
| [Architecture](docs/ARCHITECTURE.md) | components, request flow, the live-analytics outbox, security, design decisions |
| [Database](docs/DATABASE.md) | schema and ER diagram, constraints, migrations, notifications, backups and restore |
| [Backend](docs/BACKEND.md) | code layout, business rules and maths, permissions, full API reference, tests |
| [Frontend](docs/FRONTEND.md) | pages and permissions, sessions, live refresh, charts, build |
| [Client app](docs/CLIENT_APP.md) | FreshBasket Fruits and how to test with it |
| [AI setup](docs/AI_SETUP.md) | Ollama in Docker or on the host, troubleshooting |
| [Deployment](docs/DEPLOYMENT.md) | a cloud server with a domain and HTTPS |

## Project website

[`website/`](website/) is a one-page site about the project, with screenshots and the setup
steps.

- **Streamlit Community Cloud:** at <https://share.streamlit.io>, choose **Create app → Deploy a
  public app from GitHub**. Pick this repository and branch `main`, and set **Main file path** to
  `website/streamlit_app.py`. The site redeploys whenever `website/` changes on `main`.
  - Preview it locally: `pip install streamlit`, then `streamlit run website/streamlit_app.py`.
- **GitHub Pages (optional, off by default):** a repository admin sets **Settings → Pages →
  Source** to *GitHub Actions*. Then add the Actions variable `ENABLE_PAGES = true` (**Settings →
  Secrets and variables → Actions → Variables**). After that, the *Website* workflow
  (`.github/workflows/pages.yml`) deploys on every push to `website/`.
- **Locally:** open `website/index.html` directly.

## Local development (without Docker)

```bash
# Backend (Python 3.12+, from the repository root, needs PostgreSQL)
python -m venv .venv && .venv/Scripts/activate      # Windows; .venv/bin/activate elsewhere
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.main:app --reload                   # http://127.0.0.1:8000/docs
python -m backend.workers.analytics_worker          # second terminal

# Frontend
cd frontend && npm install && npm run dev           # http://localhost:5173

# Client app
cd client_app && pip install -r requirements.txt && streamlit run app.py
```

For a local run, set `DATABASE_URL` and `APP_ENV=development` in `.env`.

## Tests

```bash
pytest tests/unit                       # fast, no database
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/stockpilot_test \
  pytest tests/integration              # wipes and migrates that database
cd frontend && npm run lint && npm run build
```

CI (`.github/workflows/ci.yml`) runs on every push and pull request:
- both test suites against PostgreSQL,
- a check that the migrations render,
- the frontend lint and build,
- a Docker image build and a smoke test of the composed stack.

## Operations

| Task | Command (in Docker, prefix with `docker compose exec api`) |
|---|---|
| Create or promote an admin | `python -m backend.scripts.create_admin` |
| Apply migrations | `alembic -c backend/alembic.ini upgrade head` (the api container does this on start) |
| Rebuild analytics from source data | stop the worker, then `python -m backend.workers.rebuild [module ...]` |
| Back up now / list / restore | `docker compose exec backup backup.sh now` / `list` / `restore <file>` ([details](docs/DATABASE.md#backups-and-restore)) |
| Inspect failed analytics events | [docs/DATABASE.md](docs/DATABASE.md#useful-queries) |

All settings are environment variables, documented in [.env.example](.env.example) and declared
in [backend/core/config.py](backend/core/config.py). With `APP_ENV=production` the API refuses to
start without a strong `JWT_SECRET`.

## Project layout

```
backend/
  core/          config, auth (JWT/bcrypt), rbac, realtime (LISTEN/NOTIFY → WebSocket), database, stats
  modules/       inventory, delivery, accounts, organization, projects, business, ai
                 each: domain/ application/ infrastructure/ facade.py router.py analytics.py analytics_router.py
  outbox/        transactional outbox
  workers/       analytics worker, dispatcher, projection rebuild
  scripts/       create_admin
  alembic/       migrations
frontend/        React app (pages/, components/, context/, realtime/, lib/)
client_app/      FreshBasket Fruits: Streamlit shop app on the REST API
website/         project website (index.html, screenshots, streamlit_app.py)
docs/            documentation (see above)
ops/             backup.sh, Caddyfile
tests/           unit/ and integration/
docker-compose.yml, docker-compose.prod.yml, .env.example
```
