# Frontend

The StockPilot web app is in `frontend/`. It is built with:
- React 18 and Vite,
- Tailwind CSS 4 (through `@tailwindcss/vite`),
- React Router 7,
- Axios.

There are no UI or chart libraries; the components and SVG charts are written by hand.

## Run and build

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173, calls the API at http://127.0.0.1:8000
npm run lint      # oxlint
npm run build     # production build in dist/
```

| Build-time variable | Default | Use |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | API root. The Docker image sets `/api`, which nginx proxies to the backend |
| `VITE_WS_BASE_URL` | derived from the API URL (`http→ws`, or the page's own host for `/api`) | WebSocket root |

When you run `npm run dev` against a local API, that API's `CORS_ORIGINS` must include
`http://localhost:5173` (the default `.env.example` does).

In Docker (`frontend/Dockerfile`), Node 22 builds the app and `nginx:1.27-alpine` serves it.
`frontend/nginx.conf`:
- proxies `/api/` to `api:8000` (with WebSocket upgrade and a 300 s timeout for slow AI answers),
- caches the hashed files in `/assets/` for a year,
- serves `index.html` for every other path, so deep links like `/projects/3` work.

## Source layout

```
src/
  main.jsx               mounts <App/>
  App.jsx                routes and the permission each page needs
  config.js              API_BASE_URL, WS_BASE_URL
  api.js                 axios instance (adds the token, handles 401) and errorMessage()
  context/AuthContext.jsx  signed-in user, permissions, login/logout, can(permission)
  realtime/
    websocket.js         reconnecting, authenticated WebSocket client
    RealtimeProvider.jsx connection status + useAnalyticsRefresh(modules, callback)
  components/
    Sidebar.jsx          navigation filtered by permission, live status, sign-out
    ProtectedRoute.jsx   sign-in and permission gate for a page
    ui.jsx               Page, Panel, ErrorBanner, button/input classes, useAiStatus, InsightsPanel
    AuthCard.jsx         layout of the sign-in, sign-up and reset screens
    Markdown.jsx         safe renderer for AI answers (builds React elements, never innerHTML)
    OrgChart.jsx         reporting tree
    Pager.jsx            paging for long lists (uses the X-Total-Count header)
    charts/              LineChart, BarChart, PieChart, DonutChart, HistogramChart (SVG)
  lib/format.js          money, number, date and time formatting, time-zone offset
  pages/                 one file per screen (below)
  styles/orgChart.css    org chart connector lines
```

## Pages and permissions

`App.jsx` lists each protected route with the permission it needs. `Sidebar.jsx` hides links
the user can't open.

| Path | Page | Needs |
|---|---|---|
| `/` | Login | none |
| `/register` | Register (shown only if the server allows sign-up) | none |
| `/forgot-password`, `/reset-password` | password reset by email or admin link | none |
| `/dashboard` | Dashboard: alerts, consumption, cash, departments, live | signed in |
| `/account` | My account: change password | signed in |
| `/assistant` | AI Assistant chat | `ai.use` |
| `/inventory` | items, stock movements, history | `inventory.read` (`.write` to change) |
| `/delivery` | new order form, active and finished orders, status actions | `delivery.read` |
| `/accounts` | ledger, add credit/debit, balance | `accounts.read` |
| `/organization` | employees, departments, org chart | `organization.read` |
| `/projects`, `/projects/:id` | projects; tasks, dependencies, team, Gantt chart with critical path | `projects.read` |
| `/business` | business profile and GSTIN/PAN/CIN report | signed in (`business.manage` to edit) |
| `/roles` | Users & Roles: roles, permissions, users, reset links | `rbac.manage` |
| `/analytics` | analytics home | signed in |
| `/analytics/inventory`, `/accounts`, `/delivery`, `/organization`, `/projects` | module analytics + AI Summarize | that module's `.read` |

If a user opens a page without the permission, `ProtectedRoute` shows a "No access" message
that names the missing permission. Buttons that change data are hidden unless the user has the
`.write` permission; the API enforces the same rules.

## Sessions

- **Signing in:** `AuthContext` calls `POST /auth/login`, stores the token in
  `localStorage["token"]`, then loads `GET /auth/me`, which returns the user and their
  permissions.
- **Page refresh:** the token stays in storage and the profile is fetched again. Pages wait
  (`restoring`) until that finishes.
- **Expired or revoked tokens:** a 401 from any call fires an `auth-expired` event, and the user
  is signed out everywhere. The login call itself is excluded.
- **Permission checks in components:** `can("accounts.write")`.
- **Password change:** the server returns a new token. `replaceToken` saves it, so the current
  tab stays signed in and every other session is signed out.

## Live updates

1. When the user is signed in, `websocket.js` opens `/ws/realtime` and sends the token.
2. It reconnects with backoff, and stops if the server rejects the token (code 1008).
3. Pages subscribe to the modules they show:

   ```jsx
   useAnalyticsRefresh(["inventory", "accounts"], load);
   ```

   `load` runs about 400 ms after a matching `analytics.updated` event. Bursts of events are
   merged into one refresh.
4. The sidebar shows the connection status (Live / Connecting / Offline).

## AI in the UI

- `useAiStatus()` reads `GET /ai/status`, so pages can explain why AI is unavailable. The
  possible reasons are: disabled, the API can't reach Ollama, the model isn't downloaded, or the
  user lacks the permission.
- **Assistant page:** a chat that keeps the last messages, shows "Looked at: …" with the tools
  used, and renders answers with `Markdown.jsx`.
- **`InsightsPanel`** (on each analytics page): a Summarize button that calls `POST /ai/insights`.

## Conventions

- **Layout:** pages use `Page` (title, subtitle, actions) and `Panel` from `components/ui.jsx`.
  Don't make page-local copies.
- **Errors:** show them with `errorMessage(error)`. It flattens FastAPI's 422 validation lists
  into readable text.
- **Formatting:** use `money()`, `number()`, `date()` and `dateTime()` from `lib/format.js`.
  Times come from the API in UTC and are shown in the browser's time zone.
- **Styling:** Tailwind utility classes on a dark theme (gray-950 background, indigo accent).
