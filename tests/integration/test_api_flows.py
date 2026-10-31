from sqlalchemy import text

from backend.core.database.session import engine

from .conftest import login


def _q(sql: str):
    with engine.connect() as conn:
        return conn.execute(text(sql)).all()


# ---------------- auth & RBAC ----------------

def test_new_user_has_no_access_until_admin_assigns_role(client, admin):
    r = client.post("/auth/register", json={"email": "c@x.io", "username": "clerk", "password": "clerk-pass-1"})
    assert r.status_code == 201
    assert client.post("/auth/register", json={"email": "C@X.io", "username": "other", "password": "clerk-pass-1"}).status_code == 409

    clerk = login(client, "clerk", "clerk-pass-1")
    me = client.get("/auth/me", headers=clerk).json()
    assert me["permissions"] == []
    assert client.get("/inventory/", headers=clerk).status_code == 403

    assert client.post("/rbac/", headers=admin, json={"name": "viewer", "access": {"inventory": ["read"]}}).status_code == 201
    user_id = me["id"]
    r = client.put(f"/rbac/users/{user_id}/roles", headers=admin, json={"roles": ["viewer"]})
    assert r.status_code == 200 and r.json()["roles"] == ["viewer"]

    assert client.get("/inventory/", headers=clerk).status_code == 200
    assert client.post("/inventory/", headers=clerk, json={"name": "x", "quantity": 1, "status": "under_use"}).status_code == 403

    # Deactivated users are locked out immediately.
    assert client.patch(f"/rbac/users/{user_id}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/inventory/", headers=clerk).status_code == 401


def test_cannot_remove_last_admin(client, admin):
    me = client.get("/auth/me", headers=admin).json()
    r = client.put(f"/rbac/users/{me['id']}/roles", headers=admin, json={"roles": []})
    assert r.status_code == 400


def test_unknown_permission_rejected(client, admin):
    r = client.post("/rbac/", headers=admin, json={"name": "bad", "access": {"inventory": ["delete"]}})
    assert r.status_code == 400


# ---------------- inventory + delivery ----------------

def _item(client, admin, name="Bolt", qty=10):
    r = client.post("/inventory/", headers=admin, json={"name": name, "quantity": qty, "price": 2.5, "status": "under_use"})
    assert r.status_code == 201, r.text
    return r.json()


def test_inventory_errors_are_clean(client, admin):
    item = _item(client, admin)
    assert client.post("/inventory/", headers=admin, json={"name": "Bolt", "quantity": 1, "status": "under_use"}).status_code == 409
    r = client.put(f"/inventory/{item['id']}", headers=admin, json={"action": "consume", "quantity": 999})
    assert r.status_code == 400 and "Insufficient" in r.json()["detail"]
    assert client.delete("/inventory/99999", headers=admin).status_code == 404
    logs = client.get(f"/inventory/{item['id']}/logs", headers=admin).json()
    assert [l["action"] for l in logs] == ["add"]


def test_delivery_deducts_and_returns_linked_stock(client, admin):
    item = _item(client, admin, qty=10)
    r = client.post("/delivery/", headers=admin, json={
        "order_id": "ORD-1", "customer_id": "C1",
        "items": [{"product_name": "Bolt", "quantity": 4, "unit_price": 2.5}, {"product_name": "Gift wrap", "quantity": 1, "unit_price": 1}],
    })
    assert r.status_code == 201, r.text
    detail = client.get("/delivery/ORD-1", headers=admin).json()
    assert detail["items"][0]["inventory_item_id"] == item["id"]  # auto-linked by name
    assert detail["items"][1]["inventory_item_id"] is None

    # Illegal jump is rejected.
    assert client.put("/delivery/ORD-1/status", headers=admin, json={"status": "delivered"}).status_code == 409

    for status in ("packed", "out_for_delivery"):
        assert client.put("/delivery/ORD-1/status", headers=admin, json={"status": status}).status_code == 200
    assert client.get(f"/inventory/{item['id']}", headers=admin).json()["quantity"] == 6

    assert client.put("/delivery/ORD-1/status", headers=admin, json={"status": "failed"}).status_code == 200
    assert client.get(f"/inventory/{item['id']}", headers=admin).json()["quantity"] == 10


def test_dispatch_blocked_when_stock_insufficient(client, admin):
    _item(client, admin, qty=1)
    client.post("/delivery/", headers=admin, json={
        "order_id": "ORD-2", "customer_id": "C1", "items": [{"product_name": "Bolt", "quantity": 5, "unit_price": 1}],
    })
    client.put("/delivery/ORD-2/status", headers=admin, json={"status": "packed"})
    r = client.put("/delivery/ORD-2/status", headers=admin, json={"status": "out_for_delivery"})
    assert r.status_code == 409 and "Insufficient" in r.json()["detail"]
    assert client.get("/delivery/ORD-2", headers=admin).json()["status"] == "packed"


# ---------------- analytics pipeline ----------------

def test_delivery_items_counted_once(client, admin, run_worker):
    client.post("/delivery/", headers=admin, json={
        "order_id": "ORD-3", "customer_id": "C1", "items": [{"product_name": "Widget", "quantity": 3, "unit_price": 10}],
    })
    for status in ("packed", "out_for_delivery", "delivered"):
        client.put("/delivery/ORD-3/status", headers=admin, json={"status": status})

    statuses = run_worker()
    assert set(statuses) == {"done"}, statuses

    overview = client.get("/analytics/delivery/overview", headers=admin).json()
    items = overview["most_ordered_items"]["month"]["series"]
    assert items == [{"label": "Widget", "value": 3}]  # was 12 before the fix (counted on every status change)
    status_dist = {s["label"]: s["value"] for s in overview["status_distribution"]["month"]["series"]}
    assert status_dist == {"delivered": 1}
    assert sum(p["count"] for p in overview["moving_average"]["month"]["series"]) == 1


def test_rebuild_matches_incremental_projections(client, admin, run_worker):
    from backend.workers.rebuild import rebuild
    from backend.core.database.session import SessionLocal

    _item(client, admin, qty=50)
    client.post("/accounts/", headers=admin, json={"amount": 100.50, "transaction_type": "credit", "source_target": "A", "category": "Sales"})
    client.post("/accounts/", headers=admin, json={"amount": 40, "transaction_type": "debit", "source_target": "B", "category": "Rent"})
    client.post("/delivery/", headers=admin, json={"order_id": "ORD-4", "customer_id": "C", "items": [{"product_name": "Bolt", "quantity": 5, "unit_price": 1}]})
    for s in ("packed", "out_for_delivery", "delivered"):
        client.put("/delivery/ORD-4/status", headers=admin, json={"status": s})
    run_worker()

    tables = ["accounts_daily_totals", "accounts_daily_category_totals", "inventory_daily_consumption",
              "delivery_daily_counts", "delivery_daily_status_counts", "delivery_daily_item_counts"]
    snapshot = lambda: {t: sorted(map(tuple, _q(f"SELECT * FROM {t}")), key=str) for t in tables}  # noqa: E731
    def strip(snap):
        # Drop updated_at, and zero-count status rows that incremental updates leave
        # behind (an order moving out of "pending" leaves pending=0); the API ignores them.
        out = {t: [r[:-1] for r in rows] for t, rows in snap.items()}
        out["delivery_daily_status_counts"] = [r for r in out["delivery_daily_status_counts"] if r[2] != 0]
        return out

    before = strip(snapshot())
    db = SessionLocal()
    rebuild(db, ["accounts", "inventory", "delivery"])
    db.commit()
    db.close()
    assert strip(snapshot()) == before


def test_project_delete_does_not_poison_worker(client, admin, run_worker):
    p = client.post("/projects/", headers=admin, json={"title": "Plant", "start_date": "2026-01-01", "deadline": "2026-01-10"}).json()
    t1 = client.post(f"/projects/{p['id']}/tasks", headers=admin, json={"name": "A", "duration_days": 4}).json()
    client.post(f"/projects/{p['id']}/tasks", headers=admin, json={"name": "B", "duration_days": 8, "predecessor_task_ids": [t1["id"]]})
    run_worker()

    snap = client.get(f"/analytics/projects/project/{p['id']}", headers=admin).json()
    assert snap["critical_path"]["task_names"] == ["A", "B"]
    assert snap["schedule"]["at_risk"] is True  # 12 days of work, 9-day window

    assert client.delete(f"/projects/{p['id']}", headers=admin).status_code == 200
    statuses = run_worker()
    assert set(statuses) == {"done"}, statuses  # previously: FK violation, retried forever
    assert client.get("/analytics/projects/overview", headers=admin).json()["projects_total"] == 0


def test_org_histogram_any_bin_count(client, admin, run_worker):
    client.post("/organization/departments", headers=admin, json={"name": "Ops"})
    for i, salary in enumerate([100, 200, 300, 400]):
        client.post("/organization/employees", headers=admin, json={
            "employee_id": f"E{i}", "name": f"N{i}", "salary": salary, "job_role": "R", "departments": ["Ops"],
        })
    run_worker()
    for bins in (2, 7):
        data = client.get("/analytics/organization/overview", headers=admin, params={"histogram_bins": bins}).json()
        assert len(data["salary_histogram"]["series"]) == bins
        assert "_salaries" not in data


def test_employee_manager_cycle_rejected(client, admin):
    for eid, mgr in (("A", None), ("B", "A")):
        client.post("/organization/employees", headers=admin, json={
            "employee_id": eid, "name": eid, "salary": 1, "job_role": "r", "manager_employee_id": mgr,
        })
    r = client.put("/organization/employees/A", headers=admin, json={"manager_employee_id": "B"})
    assert r.status_code == 400 and "loop" in r.json()["detail"]


# ---------------- business verification ----------------

def test_business_verification_workflow(client, admin):
    r = client.put("/business/profile", headers=admin, json={"legal_name": "Ultra Firm", "gstin": "27AAPFU0939F1ZV"})
    body = r.json()
    assert body["verification_status"] == "format_verified"
    assert body["pan"] == "AAPFU0939F" and body["state"] == "Maharashtra"

    assert client.post("/business/profile/review", headers=admin, json={"decision": "approve"}).json()["verification_status"] == "verified"

    # Editing the GSTIN (typo) resets verification and blocks approval.
    r = client.put("/business/profile", headers=admin, json={"legal_name": "Ultra Firm", "gstin": "27AAPFU0939F1ZW", "pan": "AAPFU0939F"})
    assert r.json()["verification_status"] == "unverified"
    assert client.post("/business/profile/review", headers=admin, json={"decision": "approve"}).status_code == 409


def test_ai_status_without_ollama(client, admin):
    r = client.get("/ai/status", headers=admin)
    assert r.status_code == 200 and r.json()["can_use"] is True
