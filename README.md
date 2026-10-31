# StockPilot Enterprise

A business operating system for small manufacturers: inventory, accounts, deliveries,
organization and projects in one app, with live analytics, a local AI assistant and
offline verification of Indian business registrations (GSTIN / PAN / CIN).

```
 React (Vite) ──/api──▶ nginx ──▶ FastAPI ──▶ PostgreSQL
      ▲                               │  writes business rows + outbox events (same transaction)
      │ WebSocket                     ▼
      └──── realtime listener ◀── pg_notify ◀── analytics worker ──▶ projection tables
                                                (outbox → handlers)
 FastAPI ──▶ Ollama (local LLM, optional) for the assistant and insights
```

## Features

| Module | What it does |
|---|---|
| Inventory | Items, stock movements (receive / consume / deliver / order / return) with row locking, history, expiry dates |
| Delivery | Orders with a status workflow; items linked to inventory are deducted on dispatch and returned if the delivery fails or is cancelled |
| Accounts | Credit/debit ledger, balance and 30-day net |
| Organization | Employees, departments, reporting hierarchy (loop-proof), org chart |
| Projects | Tasks with dependencies, CPM/PERT critical path, slack and resource-conflict detection |
| Analytics | Live dashboards per module, reorder suggestions, stock-out forecast, liquidity score, schedule risk |
| Anomaly detection | Flags unusual transactions and consumption spikes (robust median/MAD statistics) |
| AI assistant | Chat with your data; read-only tools scoped to the user's permissions; runs on a local model via Ollama |
| AI insights | "Summarize" button on every analytics page |
| Business profile | GSTIN checksum, PAN/CIN format and cross-checks, then admin approval |
| Users & roles | Role-based access (`module.read` / `module.write`), user activation, admin bootstrap |
| Accounts & passwords | Change password, one-time admin reset links, optional "forgot password" emails; password changes sign out other sessions |
| Backups | Daily automatic database dumps with retention and one-command restore |

## Quick start (Docker)

Requirements: Docker Desktop (Windows/macOS) or Docker Engine + Compose v2 (Linux).

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, JWT_SECRET (32+ chars) and ADMIN_* credentials.
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build
```

Open **http://localhost:8080** and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
The API (Swagger at `/docs`) is also published on `http://localhost:8000` for the local machine only.

What starts: `db` (PostgreSQL 16, data in the `pgdata` volume), `api` (applies migrations on start),
`worker` (analytics), `web` (nginx serving the app and proxying `/api`), `backup` (daily dumps to `./backups`).

To put it on the internet with HTTPS, see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

Optional profiles:

```bash
docker compose --profile ai up -d          # + Ollama and a one-off model download (~2 GB)
docker compose --profile simulator up -d   # + Streamlit traffic simulator on http://localhost:8501
```

Stop with `docker compose down` (add `-v` to also delete the database volume).

### AI setup

AI features use [Ollama](https://ollama.com) with a small open model; nothing leaves your machine.

- **In Docker:** `docker compose --profile ai up -d`. The `ollama-pull` container downloads
  `OLLAMA_MODEL` once. Check progress with `docker compose logs -f ollama-pull`.
- **Ollama on the host instead** (uses your GPU on Windows/macOS more easily): install Ollama,
  run `ollama pull qwen2.5:3b`, and set `OLLAMA_URL=http://host.docker.internal:11434` in `.env`.

Model choice (`OLLAMA_MODEL`): `qwen2.5:3b` (default, runs on CPU with ~4 GB RAM),
`llama3.2:3b`, or `qwen2.5:7b` for noticeably better answers if you have ~8 GB RAM or a GPU.
If a model doesn't support tool calling, the assistant falls back to answering from a
pre-fetched summary of your data.

Users need the `ai.use` permission; the assistant can only read modules the user can read.
Without Ollama, the rest of the app works normally and AI buttons show as unavailable.

## Business registration verification

On **Business Profile**, an admin (`business.manage`) enters the legal name, GSTIN, PAN and
optionally CIN. The server validates offline:

- GSTIN structure, state code and **checksum** (catches typos), and that it embeds the PAN
- PAN format and holder type (company, firm, individual, …)
- CIN structure, incorporation year and company class
- Consistency: GSTIN state vs declared state vs CIN state; company CIN vs company PAN; PAN
  initial vs legal name

Passing moves the profile to *awaiting review*; an admin then compares against the
certificates and approves (*verified*) or rejects. Editing any registration field resets it.
Offline checks prove the numbers are well-formed and consistent, not that the GST portal
lists them as active; a live lookup needs a paid GSP API and can be added later.

## Backups

The `backup` service dumps the database every `BACKUP_INTERVAL_HOURS` (default 24) into `./backups`
and deletes dumps older than `BACKUP_RETENTION_DAYS` (default 14). It skips a run, and logs a warning,
if less than `BACKUP_MIN_FREE_MB` is free, so backups can never fill the disk.

```bash
docker compose exec backup backup.sh now        # back up right now
docker compose exec backup backup.sh list
docker compose stop api worker                  # restore: stop the app first
docker compose exec backup backup.sh restore stockpilot-YYYYmmdd-HHMMSS.dump
docker compose start api worker
```

Copy the files somewhere else (cloud drive, USB) from time to time; a backup on the same disk
doesn't survive that disk failing.

## Passwords

- Users change their own password under **My account** (click your name in the sidebar).
- An admin can click **Reset password** on *Users & Roles* to get a one-time link (valid
  `PASSWORD_RESET_TTL_MINUTES`, default 30) to send to the user.
- With `SMTP_*` settings in `.env`, "Forgot password?" on the login page emails the link itself.

## Local development (without Docker)

Backend (Python 3.12+; run commands from the repository root):

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; use .venv/bin/activate elsewhere
pip install -r backend/requirements.txt
# .env with DATABASE_URL, JWT_SECRET, APP_ENV=development, ADMIN_* ...
alembic -c backend/alembic.ini upgrade head
uvicorn backend.main:app --reload                   # http://127.0.0.1:8000/docs
python -m backend.workers.analytics_worker          # second terminal
```

Frontend:

```bash
cd frontend && npm install && npm run dev           # http://localhost:5173, talks to :8000
```

## Operations

| Task | Command (inside Docker prefix with `docker compose exec api`) |
|---|---|
| Create / promote an admin | `python -m backend.scripts.create_admin` |
| Apply migrations | `alembic -c backend/alembic.ini upgrade head` (the api container does this on start) |
| Rebuild analytics from source data | stop the worker, then `python -m backend.workers.rebuild [module ...]` |
| Inspect failed analytics events | `SELECT id, module, event_type, attempts, last_error FROM analytics_outbox WHERE status='dead';` then fix and `UPDATE ... SET status='pending'` |

The worker retries failed events with exponential backoff and marks them `dead` after
`OUTBOX_MAX_ATTEMPTS`, so one bad event can't block the queue. Processed events are pruned
after `OUTBOX_RETENTION_DAYS`.

### Upgrading an existing (v1) database

Migration `f1c3a9d2b7e4` converts money columns to `NUMERIC(14,2)` and timestamps to
`timestamptz` (UTC), adds stock-linked deliveries and the business profile, rebuilds the
delivery analytics (which were over-counted before) and queues organization/project
snapshot rebuilds. Back up first, then run the migration. Existing users keep their accounts;
the first admin can be granted with `create_admin`. With Neon or another pooled host, set
`DIRECT_DATABASE_URL` to the non-pooled endpoint (LISTEN/NOTIFY needs it).

## Tests

```bash
pytest tests/unit                       # fast, no database
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/stockpilot_test \
  pytest tests/integration              # wipes and migrates that database
```

CI (`.github/workflows/ci.yml`) runs both suites against PostgreSQL, lints and builds the
frontend, builds the Docker images and smoke-tests the composed stack.

## Configuration

All settings are environment variables, documented in [.env.example](.env.example) and
declared in [backend/core/config.py](backend/core/config.py). With `APP_ENV=production` the API
refuses to start without a strong `JWT_SECRET`.

## Project layout

```
backend/
  core/        config, auth (JWT/bcrypt), rbac, realtime (LISTEN/NOTIFY → WebSocket), shared analytics
  modules/     accounts, inventory, delivery, organization, projects, business, ai
               each: domain/ (pure rules) application/ (services, DTOs) infrastructure/ (models,
               repositories, projections), router.py, analytics.py (outbox handlers), analytics_router.py
  outbox/      transactional outbox
  workers/     analytics worker, dispatcher, projection rebuild
  alembic/     migrations
frontend/      React app (pages/, components/, context/, realtime/)
client_app/    Streamlit simulator that drives the REST API
tests/         unit/ and integration/
```
