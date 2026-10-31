from urllib.parse import parse_qs, urlparse

from .conftest import ADMIN, login


# ---------------- project & task editing ----------------

def _project(client, admin, **kw):
    body = {"title": "Line 2", "start_date": "2026-01-01", "deadline": "2026-01-31"} | kw
    r = client.post("/projects/", headers=admin, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _task(client, admin, pid, name, days, preds=()):
    r = client.post(f"/projects/{pid}/tasks", headers=admin,
                    json={"name": name, "duration_days": days, "predecessor_task_ids": list(preds)})
    assert r.status_code == 201, r.text
    return r.json()


def test_edit_project_fields_and_team(client, admin, run_worker):
    client.post("/organization/employees", headers=admin,
                json={"employee_id": "E1", "name": "Asha", "salary": 1, "job_role": "Eng"})
    p = _project(client, admin)

    r = client.put(f"/projects/{p['id']}", headers=admin,
                   json={"title": "Line 2 upgrade", "deadline": "2026-02-15", "resource_employee_ids": ["E1"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["title"], body["deadline"], body["resource_employee_ids"]) == ("Line 2 upgrade", "2026-02-15", ["E1"])
    assert body["start_date"] == "2026-01-01"  # untouched

    assert client.put(f"/projects/{p['id']}", headers=admin, json={"deadline": "2025-12-01"}).status_code == 400
    assert client.put(f"/projects/{p['id']}", headers=admin, json={"resource_employee_ids": ["NOPE"]}).status_code == 400
    assert set(run_worker()) == {"done"}


def test_edit_task_and_reject_dependency_loop(client, admin, run_worker):
    p = _project(client, admin)
    a = _task(client, admin, p["id"], "A", 2)
    b = _task(client, admin, p["id"], "B", 3, [a["id"]])
    c = _task(client, admin, p["id"], "C", 1, [b["id"]])

    # A -> B -> C exists; making A depend on C would loop.
    r = client.put(f"/projects/{p['id']}/tasks/{a['id']}", headers=admin, json={"predecessor_task_ids": [c["id"]]})
    assert r.status_code == 400 and "loop" in r.json()["detail"]
    r = client.put(f"/projects/{p['id']}/tasks/{a['id']}", headers=admin, json={"predecessor_task_ids": [a["id"]]})
    assert r.status_code == 400

    # Valid edits: rename, longer duration, PERT estimates, C no longer waits for B.
    r = client.put(f"/projects/{p['id']}/tasks/{b['id']}", headers=admin,
                   json={"name": "B2", "duration_days": 10, "optimistic": 8, "most_likely": 10, "pessimistic": 18})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "B2" and r.json()["pessimistic"] == 18
    r = client.put(f"/projects/{p['id']}/tasks/{c['id']}", headers=admin, json={"predecessor_task_ids": []})
    assert r.json()["predecessor_task_ids"] == []

    bad = client.put(f"/projects/{p['id']}/tasks/{b['id']}", headers=admin, json={"optimistic": 20})
    assert bad.status_code == 400  # would break optimistic <= most_likely

    sim = client.post(f"/projects/{p['id']}/simulate", headers=admin).json()
    assert sim["project_duration_days"] == 2 + (8 + 40 + 18) / 6  # A -> B2 (PERT 11)

    statuses = run_worker()
    assert set(statuses) == {"done"}, statuses
    snap = client.get(f"/analytics/projects/project/{p['id']}", headers=admin).json()
    assert snap["critical_path"]["task_names"] == ["A", "B2"]


# ---------------- passwords ----------------

def _register(client, username="worker1", password="first-pass-1"):
    r = client.post("/auth/register", json={"email": f"{username}@x.io", "username": username, "password": password})
    assert r.status_code == 201
    return r.json()


def test_change_password_signs_out_other_sessions(client):
    _register(client)
    old_session = login(client, "worker1", "first-pass-1")

    r = client.post("/auth/change-password", headers=old_session,
                    json={"current_password": "wrong", "new_password": "second-pass-2"})
    assert r.status_code == 400

    r = client.post("/auth/change-password", headers=old_session,
                    json={"current_password": "first-pass-1", "new_password": "second-pass-2"})
    assert r.status_code == 200
    new_session = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/auth/me", headers=old_session).status_code == 401  # revoked
    assert client.get("/auth/me", headers=new_session).status_code == 200
    assert client.post("/auth/login", json={"username": "worker1", "password": "first-pass-1"}).status_code == 401
    login(client, "worker1", "second-pass-2")


def test_admin_reset_link_flow(client, admin):
    user = _register(client)
    session = login(client, "worker1", "first-pass-1")

    r = client.post(f"/rbac/users/{user['id']}/reset-link", headers=admin)
    assert r.status_code == 200
    assert r.json()["emailed"] is False  # no SMTP in tests
    token = parse_qs(urlparse(r.json()["reset_url"]).query)["token"][0]

    assert client.post("/auth/reset-password", json={"token": token, "new_password": "short"}).status_code == 422
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "brand-new-pass"}).status_code == 200
    # One-time use, old sessions revoked, new password works.
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "again-new-pass"}).status_code == 400
    assert client.get("/auth/me", headers=session).status_code == 401
    login(client, "worker1", "brand-new-pass")

    # A newer link revokes older unused ones.
    first = client.post(f"/rbac/users/{user['id']}/reset-link", headers=admin).json()["reset_url"]
    client.post(f"/rbac/users/{user['id']}/reset-link", headers=admin)
    first_token = parse_qs(urlparse(first).query)["token"][0]
    assert client.post("/auth/reset-password", json={"token": first_token, "new_password": "x-new-password"}).status_code == 400


def test_forgot_password_does_not_reveal_accounts(client):
    _register(client)
    a = client.post("/auth/forgot-password", json={"email": "worker1@x.io"})
    b = client.post("/auth/forgot-password", json={"email": "nobody@x.io"})
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    assert client.post("/auth/reset-password", json={"token": "x" * 43, "new_password": "whatever-pass"}).status_code == 400


def test_auth_options_public(client):
    r = client.get("/auth/options")
    assert r.status_code == 200 and set(r.json()) == {"registration_enabled", "email_enabled"}


def test_admin_login_still_works(client):
    login(client, ADMIN["username"], ADMIN["password"])
