# StockPilot Enterprise documentation

StockPilot Enterprise is a business operating system for a small manufacturer or shop. One web
app covers inventory, deliveries, accounts, staff and projects. Its dashboards update live, and
a private AI assistant answers questions about the business's own data.

Start with the [root README](../README.md) for a quick start. The guides below go deeper.

## Guides

| Guide | Read it to learn |
|---|---|
| [User guide](USER_GUIDE.md) | how to use each page of the app, from first sign-in to analytics |
| [Architecture](ARCHITECTURE.md) | the parts of the system, how a request flows, how live updates work, and why it is built this way |
| [Database](DATABASE.md) | every table, how the modules' data relates, migrations, the event outbox and backups |
| [Backend](BACKEND.md) | the FastAPI code layout, business rules, the analytics maths, the API reference and the tests |
| [Frontend](FRONTEND.md) | the React app: pages, permissions, sessions, live refresh, charts and the build |
| [Client app](CLIENT_APP.md) | FreshBasket Fruits, the demo shop that uses StockPilot only through its REST API |
| [AI setup](AI_SETUP.md) | installing Ollama and the model, and fixing common problems |
| [Deployment](DEPLOYMENT.md) | putting StockPilot on a server with HTTPS |

## Team

| Member | Roll no. | Responsibility | Main areas of the repo |
|---|---|---|---|
| Abiram Krishna | 24CSB1A02 | Frontend and client app | `frontend/`, `client_app/` |
| Aditya Madhu | 24CSB1A03 | Backend and documentation | `backend/core/`, `backend/modules/`, `backend/workers/`, `tests/`, `docs/` |
| Aditya Shrivastava | 24CSB1A04 | Database integration, system architecture, website and deployment | `backend/alembic/`, `backend/outbox/`, `backend/core/database/`, `docker-compose*.yml`, `ops/`, `.github/`, `website/` |

## Technology at a glance

| Layer | Technology |
|---|---|
| Web app | React 18, Vite, Tailwind CSS 4, React Router 7, Axios; charts are hand-written SVG |
| API | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Uvicorn |
| Database | PostgreSQL 16 (LISTEN/NOTIFY, row locks, `SKIP LOCKED` queues), Alembic migrations |
| Background work | analytics worker process (transactional outbox → projection tables) |
| Live updates | PostgreSQL NOTIFY → API WebSocket `/ws/realtime` → browser |
| AI | Ollama running a local model (default `qwen2.5:3b`) with tool calling |
| Client app | Streamlit + `requests` |
| Packaging | Docker Compose; nginx for the web app; Caddy for HTTPS in production |
| Quality | pytest (unit and integration), oxlint, GitHub Actions CI |
