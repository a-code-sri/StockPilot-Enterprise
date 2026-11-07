# User guide

This guide is for people who use StockPilot day to day. To install it, see the
[root README](../README.md).

## Signing in

- Open the app (locally `http://localhost:8080`) and sign in with your username and password.
- **New account:** click **Create an account** if sign-up is enabled. A new account has no access
  until an administrator gives it a role.
- **Forgotten password:** use **Forgot password?** if the server can send email. Otherwise ask an
  administrator for a reset link.
- **Change your password:** click your name at the bottom of the sidebar (**My account**).
  Changing it signs you out on every other device.

The sidebar shows only the pages your role allows. The **Realtime** indicator at the bottom reads
*Live* when dashboards are updating automatically.

## Dashboard

A summary of the whole business:
- inventory alerts (exhausted, dead and expiring stock),
- consumption over the last 14 days,
- income against expenses for the last 30 days,
- headcount by department and the top executive.

It refreshes by itself whenever something changes, so you don't need to reload it.

## Inventory

- **Add an item:** name, quantity, price, optional expiry date and status.
- **Move stock** with the item's actions:

| Action | Use it when |
|---|---|
| Receive stock (+) | goods arrive. This also reduces the quantity marked as on order |
| Consume (−) | stock is used in production |
| Deliver (−) | stock leaves for a customer outside the Delivery page |
| Place order (on-order +) | you place a purchase order (adds to *on order*) |
| Return to stock (+) | goods come back |

- **History:** every item keeps a full history of its movements.
- **Limits:** stock can't go below zero, and two people can't take the same last unit.

## Delivery

1. **Create an order:** enter an order ID, a customer and one or more items. Pick each item from
   inventory, so stock is tracked.
2. **Move it along:** **Packed → Out for delivery → Delivered**. You can also mark it **Failed**,
   or **Cancel** it before it leaves.
   - Stock is deducted when the order goes **out for delivery**.
   - Stock comes back automatically if the delivery **fails** or is **cancelled**.
   - A failed delivery can be reopened for another attempt.
3. **Track it:** each order keeps a timeline of status changes, each with an optional remark.
   Active and finished orders are listed separately and can be searched.

## Accounts

- **Record a transaction:**
  - Use **credit** for money in and **debit** for money out.
  - Enter the amount, the customer or supplier, the category (for example *Sales*, *Rent*,
    *Raw material*) and optional remarks.
- **Totals:** the page shows the balance and the net of the last 30 days.
- **Finding entries:** filter by type to find an entry. Delete one if it was entered by mistake.

## Organization

- **Employees:** add employees with an ID, name, role, salary, manager and departments.
- **Org chart:** shows the reporting lines. StockPilot refuses a manager change that would
  create a loop.
- **Departments:** create and delete departments.

## Projects

1. **Create the project:** a title, description, start date and deadline, plus the team.
2. **Add tasks:** give each task a duration, or three estimates (optimistic, most likely,
   pessimistic). Add the tasks it depends on and the people assigned to it.
3. **Read the timeline.** The project page plans the timeline automatically:
   - **Critical path (red):** these tasks can't slip without delaying the whole project.
   - **Slack (blue):** how much a task can be delayed safely.
   - **Deadline:** the expected finish date and the margin left before the deadline.
   - **Resource conflicts:** people booked on two tasks at the same time.

StockPilot refuses dependency loops (A waits for B, and B waits for A).

## Analytics

Every module has an analytics page under **Analytics**. Pages update live.

| Page | Shows |
|---|---|
| Inventory | consumption trend, monthly purchase orders, reorder suggestions (how much to order to cover the next 14 days), predicted stock-out dates, near-expiry and dead stock, unusual consumption |
| Accounts | income against expenses, top categories, top customers and suppliers, a **liquidity score** (0–100, from cash flow and runway), unusual transactions |
| Delivery | deliveries per day with a moving average, most-ordered products, the status mix, busiest hours |
| Organization | headcount per department, salary distribution |
| Projects | schedule risk and critical-path status across all projects |

"Unusual" means far from the typical value for that category. StockPilot uses a statistical test
that one-off spikes can't distort.

**Summarize** (AI insights) writes a short briefing of the page with recommended actions.

## AI Assistant

Ask questions in plain language, for example:
- *Which items will run out first?*
- *What were our biggest expenses this month?*
- *Which deliveries are still out?*
- *Is project Alpha on schedule?*

- **Read-only:** the assistant can only read data, and only the modules your role can see. It
  can't change anything.
- **Sources:** each answer lists the data it looked at.
- **Speed:** answers come from a model running on your own server. Without a GPU they take 10–30
  seconds.

If the page says the assistant is unavailable, an administrator should follow
[AI_SETUP.md](AI_SETUP.md).

## Business profile

- **Enter the details:** the company's legal name, GSTIN, PAN and optionally CIN.
- **Automatic checks:** StockPilot checks the formats and the GSTIN checksum. It also checks that
  the numbers agree with each other and with the declared state.
- **Review:** a passing profile waits for an administrator to compare it against the
  certificates and approve it. Changing a number sends it back for review.

## Users & Roles (administrators)

- **Roles:** create roles (for example `warehouse_manager`) and tick the permissions each one
  gives. `read` lets someone view a module and its analytics; `write` lets them change it.
- **Users:** give users their roles, deactivate a user who leaves, or create a one-time
  **password reset link** to send them.
- **The `admin` role:** always has every permission.
