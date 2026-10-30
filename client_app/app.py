from __future__ import annotations

import json
import os
import random
import string
from datetime import date, timedelta
from typing import Any

import requests
import streamlit as st


# ============================================================
# Configuration
# ============================================================

st.set_page_config(
    page_title="StockPilot Enterprise Simulator",
    page_icon="🏢",
    layout="wide",
)

DEFAULT_BACKEND_URL = os.getenv("STOCKPILOT_API_URL", "http://127.0.0.1:8000")


# ============================================================
# Session state
# ============================================================

DEFAULT_STATE = {
    "token": None,
    "user": None,
    "activity": [],
    "last_response": None,
    "selected_project_id": None,
    "created_employee_ids": [],
    "created_inventory_names": [],
    "created_order_ids": [],
}


for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# Helpers
# ============================================================

def backend_url() -> str:
    return st.session_state.get(
        "backend_url",
        DEFAULT_BACKEND_URL,
    ).rstrip("/")


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("token")

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def add_activity(
    operation: str,
    method: str,
    endpoint: str,
    status: int | str,
    detail: Any = None,
) -> None:
    entry = {
        "operation": operation,
        "method": method,
        "endpoint": endpoint,
        "status": status,
        "detail": detail,
    }

    st.session_state.activity.insert(0, entry)

    # Keep the activity panel bounded.
    st.session_state.activity = (
        st.session_state.activity[:100]
    )


def api_request(
    method: str,
    endpoint: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    operation: str = "API request",
    timeout: int = 15,
) -> tuple[bool, Any]:
    """
    Central REST client.

    The Streamlit application deliberately knows nothing about
    PostgreSQL, analytics_outbox, pg_notify, or WebSockets.
    """

    url = f"{backend_url()}{endpoint}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=auth_headers(),
            json=json_body,
            params=params,
            timeout=timeout,
        )

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        st.session_state.last_response = {
            "status_code": response.status_code,
            "method": method,
            "endpoint": endpoint,
            "payload": payload,
        }

        add_activity(
            operation=operation,
            method=method,
            endpoint=endpoint,
            status=response.status_code,
            detail=payload,
        )

        if response.ok:
            return True, payload

        return False, payload

    except requests.RequestException as exc:
        detail = f"{type(exc).__name__}: {exc}"

        st.session_state.last_response = {
            "status_code": "ERROR",
            "method": method,
            "endpoint": endpoint,
            "payload": detail,
        }

        add_activity(
            operation=operation,
            method=method,
            endpoint=endpoint,
            status="ERROR",
            detail=detail,
        )

        return False, detail


def show_result(
    success: bool,
    payload: Any,
    success_message: str | None = None,
) -> None:
    if success:
        if success_message:
            st.success(success_message)

        with st.expander("API response", expanded=False):
            st.json(payload)

    else:
        st.error("API request failed")

        with st.expander("Error response", expanded=True):
            if isinstance(payload, (dict, list)):
                st.json(payload)
            else:
                st.code(str(payload))


def random_suffix(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def make_inventory_name(prefix: str = "Enterprise Item") -> str:
    return f"{prefix} {random_suffix()}"


def inventory_path(name: str, suffix: str = "") -> str | None:
    """
    The API addresses inventory items by id. Resolve an item name (as typed or
    remembered by this simulator) to `/inventory/{id}{suffix}`; None if not found.
    """
    ok, payload = api_request(
        "GET",
        "/inventory/",
        params={"search": name, "limit": 50},
        operation=f"Look up inventory '{name}'",
    )
    if ok:
        for item in payload:
            if item.get("name") == name:
                return f"/inventory/{item['id']}{suffix}"
    st.error(f"Inventory item '{name}' was not found.")
    return None


def make_order_id() -> str:
    return f"ACME-ORD-{random_suffix(8)}"


def make_employee_id() -> str:
    return f"EMP-{random_suffix(6)}"


def make_project_title() -> str:
    return f"Enterprise Project {random_suffix(6)}"


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("🏢 StockPilot")
st.sidebar.caption("Enterprise Client Simulator")

backend_input = st.sidebar.text_input(
    "FastAPI Backend URL",
    value=st.session_state.get(
        "backend_url",
        DEFAULT_BACKEND_URL,
    ),
)

st.session_state.backend_url = backend_input.rstrip("/")

st.sidebar.divider()

if st.session_state.token:
    st.sidebar.success("Authenticated")

    user = st.session_state.user or {}

    st.sidebar.write(
        f"**User:** {user.get('username', 'unknown')}"
    )

    roles = user.get("roles", [])

    if roles:
        role_names = [
            role.get("name", "")
            if isinstance(role, dict)
            else str(role)
            for role in roles
        ]

        st.sidebar.write(
            f"**Roles:** {', '.join(role_names)}"
        )

    if st.sidebar.button(
        "Logout",
        use_container_width=True,
    ):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

else:
    st.sidebar.info("Not authenticated")


# ============================================================
# Header
# ============================================================

st.title("🏢 StockPilot Enterprise Simulator")

st.markdown(
    """
This application acts as a **separate enterprise client**.

It only communicates with the StockPilot backend through REST APIs.

**REST → FastAPI → PostgreSQL → Analytics Worker → pg_notify →
FastAPI WebSocket → React Analytics Dashboard**
"""
)

st.caption(
    f"Backend: `{backend_url()}`"
)


# ============================================================
# Authentication
# ============================================================

if not st.session_state.token:

    st.header("🔐 Enterprise Client Authentication")

    login_tab, register_tab = st.tabs(
        ["Login", "Register"]
    )

    with login_tab:

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                value="",
            )

            password = st.text_input(
                "Password",
                type="password",
            )

            login_clicked = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if login_clicked:

            success, payload = api_request(
                "POST",
                "/auth/login",
                json_body={
                    "username": username,
                    "password": password,
                },
                operation="Enterprise login",
            )

            if success:

                token = payload.get("access_token")

                if not token:
                    st.error(
                        "Backend returned a successful response "
                        "without an access token."
                    )
                else:
                    st.session_state.token = token

                    # Fetch current user using the actual backend
                    # /auth/me endpoint.
                    me_success, me_payload = api_request(
                        "GET",
                        "/auth/me",
                        operation="Fetch authenticated enterprise user",
                    )

                    if me_success:
                        st.session_state.user = me_payload

                    st.success("Enterprise client authenticated.")

                    st.rerun()

            else:
                show_result(False, payload)

    with register_tab:

        st.info(
            "Register a dedicated simulator user if you do not "
            "already have an account. New users have no role: an "
            "admin must assign one on the web app's Users & Roles "
            "page (or sign in here as the bootstrap admin)."
        )

        with st.form("register_form"):

            register_email = st.text_input(
                "Email",
                value="enterprise.simulator@example.com",
            )

            register_username = st.text_input(
                "Username",
                value="enterprise_simulator",
            )

            register_password = st.text_input(
                "Password",
                type="password",
                value="Enterprise123!",
            )

            register_clicked = st.form_submit_button(
                "Register",
                use_container_width=True,
            )

        if register_clicked:

            success, payload = api_request(
                "POST",
                "/auth/register",
                json_body={
                    "email": register_email,
                    "username": register_username,
                    "password": register_password,
                },
                operation="Register enterprise simulator",
            )

            show_result(
                success,
                payload,
                "Simulator user registered. You can now log in.",
            )

    st.stop()


# ============================================================
# Authenticated application
# ============================================================

tabs = st.tabs(
    [
        "📊 Test Control Center",
        "📦 Inventory",
        "💰 Accounts",
        "🚚 Delivery",
        "👥 Organization",
        "📋 Projects",
        "🔍 Read APIs",
        "🧪 Activity Log",
    ]
)


# ============================================================
# TEST CONTROL CENTER
# ============================================================

with tabs[0]:

    st.header("📊 Realtime Test Control Center")

    st.markdown(
        """
Use this page to run a complete end-to-end realtime test.

Keep the **React StockPilot Analytics dashboard open in another
browser tab/window** while pressing these buttons.
"""
    )

    st.subheader("Recommended test sequence")

    st.markdown(
        """
**1. Inventory**

Create inventory → add stock → consume stock → change status.

Watch the React Inventory Analytics page.

**2. Accounts**

Create credit → create debit.

Watch the Accounts Analytics page.

**3. Delivery**

Create delivery → packed → out for delivery → delivered.

Watch the Delivery Analytics page.

**4. Organization**

Create department → create employees.

Watch Organization Analytics.

**5. Projects**

Create project → create tasks → simulate project.

Watch Project Analytics if its projection is wired to realtime events.
"""
    )

    st.divider()

    st.subheader("⚡ One-click smoke test")

    if st.button(
        "Run Full Enterprise Activity Scenario",
        type="primary",
        use_container_width=True,
    ):

        progress = st.progress(0)
        status_box = st.empty()

        # ----------------------------------------------------
        # Inventory
        # ----------------------------------------------------

        status_box.write("📦 Creating inventory item...")

        inventory_name = make_inventory_name()

        success, payload = api_request(
            "POST",
            "/inventory/",
            json_body={
                "name": inventory_name,
                "quantity": 100,
                "on_order_quantity": 20,
                "price": 1250.0,
                "status": "under_use",
                "expiry_date": (
                    date.today() + timedelta(days=120)
                ).isoformat(),
            },
            operation="Smoke test: create inventory",
        )

        if success:
            st.session_state.created_inventory_names.append(
                inventory_name
            )

        progress.progress(15)

        # ----------------------------------------------------
        # Inventory consume
        # ----------------------------------------------------

        status_box.write("📦 Consuming inventory...")

        api_request(
            "PUT",
            inventory_path(inventory_name) or "/inventory/0",
            json_body={
                "quantity": 15,
                "action": "consume",
            },
            operation="Smoke test: consume inventory",
        )

        progress.progress(25)

        # ----------------------------------------------------
        # Accounts
        # ----------------------------------------------------

        status_box.write("💰 Creating account transactions...")

        api_request(
            "POST",
            "/accounts/",
            json_body={
                "amount": 25000,
                "transaction_type": "credit",
                "source_target": "Acme Enterprise Client",
                "category": "Customer Payment",
                "remarks": "Realtime smoke test credit",
            },
            operation="Smoke test: account credit",
        )

        api_request(
            "POST",
            "/accounts/",
            json_body={
                "amount": 8500,
                "transaction_type": "debit",
                "source_target": "Enterprise Supplier",
                "category": "Inventory Purchase",
                "remarks": "Realtime smoke test debit",
            },
            operation="Smoke test: account debit",
        )

        progress.progress(40)

        # ----------------------------------------------------
        # Organization
        # ----------------------------------------------------

        status_box.write("👥 Creating enterprise department...")

        department_name = (
            f"Realtime Operations {random_suffix(4)}"
        )

        success, payload = api_request(
            "POST",
            "/organization/departments",
            json_body={
                "name": department_name,
            },
            operation="Smoke test: create department",
        )

        progress.progress(55)

        # ----------------------------------------------------
        # Employee
        # ----------------------------------------------------

        status_box.write("👤 Creating enterprise employee...")

        employee_id = make_employee_id()

        success, payload = api_request(
            "POST",
            "/organization/employees",
            json_body={
                "employee_id": employee_id,
                "name": "Realtime Test Employee",
                "salary": 85000,
                "job_role": "Operations Engineer",
                "manager_employee_id": None,
                "departments": [department_name],
            },
            operation="Smoke test: create employee",
        )

        if success:
            st.session_state.created_employee_ids.append(
                employee_id
            )

        progress.progress(65)

        # ----------------------------------------------------
        # Delivery
        # ----------------------------------------------------

        status_box.write("🚚 Creating delivery...")

        order_id = make_order_id()

        success, payload = api_request(
            "POST",
            "/delivery/",
            json_body={
                "order_id": order_id,
                "customer_id": "ACME-CUSTOMER-001",
                "items": [
                    {
                        "product_name": inventory_name,
                        "quantity": 5,
                        "unit_price": 1250.0,
                    },
                    {
                        "product_name": "Enterprise Component",
                        "quantity": 2,
                        "unit_price": 2500.0,
                    },
                ],
                "remarks": "Realtime enterprise smoke test",
            },
            operation="Smoke test: create delivery",
        )

        if success:
            st.session_state.created_order_ids.append(
                order_id
            )

        progress.progress(75)

        # ----------------------------------------------------
        # Delivery status transitions
        # ----------------------------------------------------

        status_box.write("🚚 Advancing delivery status...")

        delivery_statuses = [
            "packed",
            "out_for_delivery",
            "delivered",
        ]

        for delivery_status in delivery_statuses:

            api_request(
                "PUT",
                f"/delivery/{order_id}/status",
                json_body={
                    "status": delivery_status,
                    "remark": (
                        f"Realtime smoke test: "
                        f"{delivery_status}"
                    ),
                },
                operation=(
                    f"Smoke test: delivery → "
                    f"{delivery_status}"
                ),
            )

        progress.progress(90)

        # ----------------------------------------------------
        # Final inventory status
        # ----------------------------------------------------

        status_box.write(
            "📦 Updating final inventory state..."
        )

        api_request(
            "PUT",
            inventory_path(inventory_name, "/status") or "/inventory/0/status",
            json_body={
                "status": "ordered",
            },
            operation="Smoke test: inventory status",
        )

        progress.progress(100)

        status_box.success(
            "Complete enterprise realtime scenario finished."
        )

        st.info(
            """
Now look at the React analytics dashboards.

The Streamlit application itself never sends a WebSocket event.
If the analytics dashboards changed automatically, the complete
pipeline worked:

REST → DB → outbox → worker → projection → pg_notify →
FastAPI listener → WebSocket → React → REST refresh.
"""
        )


# ============================================================
# INVENTORY
# ============================================================

with tabs[1]:

    st.header("📦 Inventory Operations")

    create_col, update_col = st.columns(2)

    with create_col:

        st.subheader("Create Inventory")

        with st.form("create_inventory_form"):

            name = st.text_input(
                "Item name",
                value=make_inventory_name(),
            )

            quantity = st.number_input(
                "Initial quantity",
                min_value=0,
                value=100,
                step=1,
            )

            on_order = st.number_input(
                "On-order quantity",
                min_value=0,
                value=20,
                step=1,
            )

            price = st.number_input(
                "Unit price",
                min_value=0.0,
                value=1000.0,
                step=100.0,
            )

            status = st.selectbox(
                "Status",
                [
                    "under_use",
                    "ordered",
                    "consumed",
                ],
            )

            expiry = st.date_input(
                "Expiry date",
                value=date.today() + timedelta(days=90),
            )

            clicked = st.form_submit_button(
                "Create inventory",
                use_container_width=True,
            )

        if clicked:

            success, payload = api_request(
                "POST",
                "/inventory/",
                json_body={
                    "name": name,
                    "quantity": quantity,
                    "on_order_quantity": on_order,
                    "price": price,
                    "status": status,
                    "expiry_date": expiry.isoformat(),
                },
                operation="Create inventory",
            )

            if success:
                st.session_state.created_inventory_names.append(
                    name
                )

            show_result(
                success,
                payload,
                "Inventory item created.",
            )

    with update_col:

        st.subheader("Modify Inventory")

        existing_name = st.text_input(
            "Inventory name",
            value=(
                st.session_state.created_inventory_names[-1]
                if st.session_state.created_inventory_names
                else ""
            ),
        )

        inventory_action = st.selectbox(
            "Action",
            [
                "add",
                "consume",
                "deliver",
                "order",
                "return",
            ],
        )

        inventory_quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=10,
            step=1,
        )

        if st.button(
            "Execute inventory action",
            use_container_width=True,
        ):

            path = inventory_path(existing_name)
            success, payload = (False, "Not found") if not path else api_request(
                "PUT",
                path,
                json_body={
                    "quantity": inventory_quantity,
                    "action": inventory_action,
                },
                operation=(
                    f"Inventory {inventory_action}"
                ),
            )

            show_result(
                success,
                payload,
                f"Inventory {inventory_action} operation completed.",
            )

        new_status = st.selectbox(
            "New status",
            [
                "under_use",
                "ordered",
                "consumed",
            ],
            key="inventory_status_select",
        )

        if st.button(
            "Change inventory status",
            use_container_width=True,
        ):

            path = inventory_path(existing_name, "/status")
            success, payload = (False, "Not found") if not path else api_request(
                "PUT",
                path,
                json_body={
                    "status": new_status,
                },
                operation="Inventory status update",
            )

            show_result(
                success,
                payload,
                "Inventory status updated.",
            )

        if st.button(
            "Delete inventory item",
            use_container_width=True,
        ):

            path = inventory_path(existing_name)
            success, payload = (False, "Not found") if not path else api_request(
                "DELETE",
                path,
                operation="Delete inventory",
            )

            show_result(
                success,
                payload,
                "Inventory item deleted.",
            )


# ============================================================
# ACCOUNTS
# ============================================================

with tabs[2]:

    st.header("💰 Accounts Operations")

    transaction_type = st.radio(
        "Transaction type",
        ["credit", "debit"],
        horizontal=True,
    )

    with st.form("account_transaction_form"):

        amount = st.number_input(
            "Amount",
            min_value=0.01,
            value=10000.0,
            step=500.0,
        )

        source_target = st.text_input(
            "Source / Target",
            value="Acme Enterprise",
        )

        category = st.text_input(
            "Category",
            value=(
                "Customer Payment"
                if transaction_type == "credit"
                else "Supplier Payment"
            ),
        )

        remarks = st.text_area(
            "Remarks",
            value="Enterprise realtime test transaction",
        )

        clicked = st.form_submit_button(
            "Create transaction",
            use_container_width=True,
        )

    if clicked:

        success, payload = api_request(
            "POST",
            "/accounts/",
            json_body={
                "amount": amount,
                "transaction_type": transaction_type,
                "source_target": source_target,
                "category": category,
                "remarks": remarks,
            },
            operation=(
                f"Create account {transaction_type}"
            ),
        )

        show_result(
            success,
            payload,
            "Account transaction created.",
        )


# ============================================================
# DELIVERY
# ============================================================

with tabs[3]:

    st.header("🚚 Delivery Operations")

    st.subheader("Create Delivery")

    with st.form("create_delivery_form"):

        order_id = st.text_input(
            "Order ID",
            value=make_order_id(),
        )

        customer_id = st.text_input(
            "Customer ID",
            value="ACME-CUSTOMER-001",
        )

        remarks = st.text_area(
            "Remarks",
            value="Enterprise simulator delivery",
        )

        item_1, item_2 = st.columns(2)

        with item_1:

            product_1 = st.text_input(
                "Product 1",
                value="Industrial Component",
            )

            quantity_1 = st.number_input(
                "Quantity 1",
                min_value=1,
                value=5,
                step=1,
            )

            price_1 = st.number_input(
                "Unit price 1",
                min_value=0.0,
                value=1500.0,
                step=100.0,
            )

        with item_2:

            product_2 = st.text_input(
                "Product 2",
                value="Replacement Part",
            )

            quantity_2 = st.number_input(
                "Quantity 2",
                min_value=1,
                value=2,
                step=1,
            )

            price_2 = st.number_input(
                "Unit price 2",
                min_value=0.0,
                value=2500.0,
                step=100.0,
            )

        clicked = st.form_submit_button(
            "Create delivery",
            use_container_width=True,
        )

    if clicked:

        success, payload = api_request(
            "POST",
            "/delivery/",
            json_body={
                "order_id": order_id,
                "customer_id": customer_id,
                "items": [
                    {
                        "product_name": product_1,
                        "quantity": quantity_1,
                        "unit_price": price_1,
                    },
                    {
                        "product_name": product_2,
                        "quantity": quantity_2,
                        "unit_price": price_2,
                    },
                ],
                "remarks": remarks,
            },
            operation="Create delivery",
        )

        if success:
            st.session_state.created_order_ids.append(
                order_id
            )

        show_result(
            success,
            payload,
            f"Delivery {order_id} created.",
        )

    st.divider()

    st.subheader("Update Delivery Status")

    selected_order = st.text_input(
        "Order ID",
        value=(
            st.session_state.created_order_ids[-1]
            if st.session_state.created_order_ids
            else ""
        ),
        key="delivery_update_order",
    )

    status = st.selectbox(
        "Status",
        [
            "pending",
            "packed",
            "out_for_delivery",
            "delivered",
            "failed",
            "cancelled",
        ],
    )

    remark = st.text_input(
        "Status remark",
        value="Updated by enterprise simulator",
    )

    if st.button(
        "Update delivery status",
        use_container_width=True,
    ):

        success, payload = api_request(
            "PUT",
            f"/delivery/{selected_order}/status",
            json_body={
                "status": status,
                "remark": remark,
            },
            operation=(
                f"Delivery status → {status}"
            ),
        )

        show_result(
            success,
            payload,
            f"Delivery status changed to {status}.",
        )


# ============================================================
# ORGANIZATION
# ============================================================

with tabs[4]:

    st.header("👥 Organization Operations")

    department_col, employee_col = st.columns(2)

    with department_col:

        st.subheader("Create Department")

        department_name = st.text_input(
            "Department name",
            value=f"Operations {random_suffix(4)}",
            key="department_name",
        )

        if st.button(
            "Create department",
            use_container_width=True,
        ):

            success, payload = api_request(
                "POST",
                "/organization/departments",
                json_body={
                    "name": department_name,
                },
                operation="Create department",
            )

            show_result(
                success,
                payload,
                "Department created.",
            )

    with employee_col:

        st.subheader("Create Employee")

        employee_id = st.text_input(
            "Employee ID",
            value=make_employee_id(),
            key="employee_id",
        )

        employee_name = st.text_input(
            "Employee name",
            value="Enterprise Test Employee",
        )

        salary = st.number_input(
            "Salary",
            min_value=0.0,
            value=75000.0,
            step=5000.0,
        )

        job_role = st.text_input(
            "Job role",
            value="Operations Engineer",
        )

        employee_department = st.text_input(
            "Department name",
            value=department_name,
        )

        manager_employee_id = st.text_input(
            "Manager employee ID (optional)",
            value="",
        )

        if st.button(
            "Create employee",
            use_container_width=True,
        ):

            departments = [
                employee_department
            ] if employee_department.strip() else []

            success, payload = api_request(
                "POST",
                "/organization/employees",
                json_body={
                    "employee_id": employee_id,
                    "name": employee_name,
                    "salary": salary,
                    "job_role": job_role,
                    "manager_employee_id": (
                        manager_employee_id.strip()
                        or None
                    ),
                    "departments": departments,
                },
                operation="Create employee",
            )

            if success:
                st.session_state.created_employee_ids.append(
                    employee_id
                )

            show_result(
                success,
                payload,
                "Employee created.",
            )

    st.divider()

    st.subheader("Delete Employee")

    delete_employee_id = st.text_input(
        "Employee ID to delete",
        value=(
            st.session_state.created_employee_ids[-1]
            if st.session_state.created_employee_ids
            else ""
        ),
    )

    if st.button(
        "Delete employee",
        use_container_width=True,
    ):

        success, payload = api_request(
            "DELETE",
            f"/organization/employees/{delete_employee_id}",
            operation="Delete employee",
        )

        show_result(
            success,
            payload,
            "Employee deleted.",
        )


# ============================================================
# PROJECTS
# ============================================================

with tabs[5]:

    st.header("📋 Project Operations")

    st.subheader("Create Project")

    with st.form("create_project_form"):

        project_title = st.text_input(
            "Project title",
            value=make_project_title(),
        )

        project_description = st.text_area(
            "Description",
            value="Enterprise realtime analytics test project",
        )

        start_date = st.date_input(
            "Start date",
            value=date.today(),
        )

        deadline = st.date_input(
            "Deadline",
            value=date.today() + timedelta(days=30),
        )

        resource_ids = st.text_input(
            "Resource employee IDs",
            value="",
            help="Comma-separated employee IDs.",
        )

        clicked = st.form_submit_button(
            "Create project",
            use_container_width=True,
        )

    if clicked:

        resources = [
            item.strip()
            for item in resource_ids.split(",")
            if item.strip()
        ]

        success, payload = api_request(
            "POST",
            "/projects/",
            json_body={
                "title": project_title,
                "description": project_description,
                "start_date": start_date.isoformat(),
                "deadline": deadline.isoformat(),
                "resource_employee_ids": resources,
            },
            operation="Create project",
        )

        if success and isinstance(payload, dict):
            st.session_state.selected_project_id = payload.get(
                "id"
            )

        show_result(
            success,
            payload,
            "Project created.",
        )

    st.divider()

    st.subheader("Create Task")

    project_id_input = st.number_input(
        "Project ID",
        min_value=1,
        value=(
            st.session_state.selected_project_id or 1
        ),
        step=1,
    )

    with st.form("create_task_form"):

        task_name = st.text_input(
            "Task name",
            value=f"Realtime Task {random_suffix(4)}",
        )

        task_description = st.text_area(
            "Task description",
            value="Task generated by enterprise simulator",
        )

        duration_days = st.number_input(
            "Duration days",
            min_value=0.1,
            value=5.0,
            step=0.5,
        )

        optimistic = st.number_input(
            "Optimistic duration",
            min_value=0.1,
            value=3.0,
            step=0.5,
        )

        most_likely = st.number_input(
            "Most likely duration",
            min_value=0.1,
            value=5.0,
            step=0.5,
        )

        pessimistic = st.number_input(
            "Pessimistic duration",
            min_value=0.1,
            value=8.0,
            step=0.5,
        )

        predecessor_ids = st.text_input(
            "Predecessor task IDs",
            value="",
            help="Comma-separated task IDs.",
        )

        task_resources = st.text_input(
            "Resource employee IDs",
            value="",
            help="Comma-separated employee IDs.",
        )

        clicked = st.form_submit_button(
            "Create task",
            use_container_width=True,
        )

    if clicked:

        predecessors = []

        for item in predecessor_ids.split(","):
            item = item.strip()

            if item:
                try:
                    predecessors.append(int(item))
                except ValueError:
                    pass

        resources = [
            item.strip()
            for item in task_resources.split(",")
            if item.strip()
        ]

        success, payload = api_request(
            "POST",
            f"/projects/{int(project_id_input)}/tasks",
            json_body={
                "name": task_name,
                "description": task_description,
                "duration_days": duration_days,
                "optimistic": optimistic,
                "most_likely": most_likely,
                "pessimistic": pessimistic,
                "predecessor_task_ids": predecessors,
                "resource_employee_ids": resources,
            },
            operation="Create project task",
        )

        show_result(
            success,
            payload,
            "Project task created.",
        )

    st.divider()

    st.subheader("Project Simulation")

    if st.button(
        "Run Project Simulation",
        use_container_width=True,
    ):

        success, payload = api_request(
            "POST",
            f"/projects/{int(project_id_input)}/simulate",
            operation="Run project simulation",
        )

        show_result(
            success,
            payload,
            "Project simulation completed.",
        )

    st.divider()

    st.subheader("Delete Project")

    if st.button(
        "Delete selected project",
        use_container_width=True,
    ):

        success, payload = api_request(
            "DELETE",
            f"/projects/{int(project_id_input)}",
            operation="Delete project",
        )

        show_result(
            success,
            payload,
            "Project deleted.",
        )


# ============================================================
# READ APIs
# ============================================================

with tabs[6]:

    st.header("🔍 Read / Verification APIs")

    st.caption(
        "These operations are useful for confirming that the "
        "backend state changed independently of the realtime path."
    )

    read_module = st.selectbox(
        "Module",
        [
            "Inventory",
            "Accounts",
            "Delivery Active",
            "Delivery Finished",
            "Organization Departments",
            "Organization Employees",
            "Projects",
        ],
    )

    if st.button(
        "Fetch current data",
        type="primary",
        use_container_width=True,
    ):

        if read_module == "Inventory":

            success, payload = api_request(
                "GET",
                "/inventory/",
                operation="Read inventory",
            )

        elif read_module == "Accounts":

            success, payload = api_request(
                "GET",
                "/accounts/",
                operation="Read accounts",
            )

        elif read_module == "Delivery Active":

            success, payload = api_request(
                "GET",
                "/delivery/active",
                operation="Read active deliveries",
            )

        elif read_module == "Delivery Finished":

            success, payload = api_request(
                "GET",
                "/delivery/finished",
                operation="Read finished deliveries",
            )

        elif read_module == "Organization Departments":

            success, payload = api_request(
                "GET",
                "/organization/departments",
                operation="Read departments",
            )

        elif read_module == "Organization Employees":

            success, payload = api_request(
                "GET",
                "/organization/employees",
                operation="Read employees",
            )

        else:

            success, payload = api_request(
                "GET",
                "/projects/",
                operation="Read projects",
            )

        show_result(
            success,
            payload,
        )


# ============================================================
# ACTIVITY LOG
# ============================================================

with tabs[7]:

    st.header("🧪 Enterprise Client Activity")

    st.caption(
        "Every operation performed by this client is recorded "
        "here. This is useful while debugging the realtime flow."
    )

    if st.button(
        "Clear activity log",
        use_container_width=True,
    ):
        st.session_state.activity = []
        st.rerun()

    if not st.session_state.activity:

        st.info("No API operations performed yet.")

    else:

        for index, entry in enumerate(
            st.session_state.activity
        ):

            status = entry["status"]

            if isinstance(status, int) and 200 <= status < 300:
                icon = "🟢"
            else:
                icon = "🔴"

            with st.expander(
                f"{icon} "
                f"{entry['method']} "
                f"{entry['endpoint']} "
                f"→ {status}",
                expanded=False,
            ):

                st.write(
                    f"**Operation:** "
                    f"{entry['operation']}"
                )

                detail = entry.get("detail")

                if isinstance(
                    detail,
                    (dict, list),
                ):
                    st.json(detail)
                else:
                    st.code(str(detail))


# ============================================================
# Last API response
# ============================================================

st.divider()

with st.expander(
    "Last API response",
    expanded=False,
):

    if st.session_state.last_response:

        st.json(
            st.session_state.last_response
        )

    else:

        st.info(
            "No API request has been performed yet."
        )