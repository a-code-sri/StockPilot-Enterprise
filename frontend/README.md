# StockPilot web app

React 18 + Vite + Tailwind. The full guide is [docs/FRONTEND.md](../docs/FRONTEND.md).

```bash
npm install
npm run dev      # http://localhost:5173 (expects the API on http://127.0.0.1:8000)
npm run build    # production build in dist/
npm run lint
```

Environment (optional, build-time): `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`;
the Docker image uses `/api` behind nginx) and `VITE_WS_BASE_URL` (derived from the API URL
when unset).
