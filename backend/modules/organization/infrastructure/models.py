from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Table,
    UniqueConstraint,
    CheckConstraint,
    event,
)
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import insert

from backend.core.database.base import Base
from backend.outbox.models import AnalyticsOutbox

employee_departments = Table(
    "employee_departments",
    Base.metadata,
    Column("employee_db_id", Integer, ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", Integer, ForeignKey("departments.id", ondelete="RESTRICT"), primary_key=True),
)


class DepartmentModel(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class EmployeeModel(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)

    # Business-facing employee id
    employee_id = Column(String, nullable=False, unique=True, index=True)

    name = Column(String, nullable=False, index=True)
    salary = Column(Float, nullable=False)
    job_role = Column(String, nullable=False, index=True)

    # Self-referential manager FK (uses internal DB id)
    manager_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    manager = relationship("EmployeeModel", remote_side=[id], backref="subordinates", foreign_keys=[manager_id])

    departments = relationship(
        "DepartmentModel",
        secondary=employee_departments,
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_employee_salary_non_negative"),
        UniqueConstraint("employee_id", name="uq_employee_employee_id"),
    )


def _emit_org_changed(connection, *, reason: str, entity: str | None = None, entity_id: str | None = None):
    payload = {
        "reason": reason,
        "entity": entity,
        "entity_id": entity_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # keep bins default here; handler defaults to 10 anyway
        "histogram_bins": 10,
    }
    connection.execute(
        insert(AnalyticsOutbox).values(
            module="organization",
            event_type="org_changed",
            aggregate_type="org",
            aggregate_id="1",
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )


@event.listens_for(EmployeeModel, "after_insert")
def org_after_employee_insert(mapper, connection, target: EmployeeModel):
    _emit_org_changed(connection, reason="employee_insert", entity="employee", entity_id=str(target.id))


@event.listens_for(EmployeeModel, "after_update")
def org_after_employee_update(mapper, connection, target: EmployeeModel):
    _emit_org_changed(connection, reason="employee_update", entity="employee", entity_id=str(target.id))


@event.listens_for(EmployeeModel, "after_delete")
def org_after_employee_delete(mapper, connection, target: EmployeeModel):
    _emit_org_changed(connection, reason="employee_delete", entity="employee", entity_id=str(getattr(target, "id", "")))


@event.listens_for(DepartmentModel, "after_insert")
def org_after_department_insert(mapper, connection, target: DepartmentModel):
    _emit_org_changed(connection, reason="department_insert", entity="department", entity_id=str(target.id))


@event.listens_for(DepartmentModel, "after_update")
def org_after_department_update(mapper, connection, target: DepartmentModel):
    _emit_org_changed(connection, reason="department_update", entity="department", entity_id=str(target.id))


@event.listens_for(DepartmentModel, "after_delete")
def org_after_department_delete(mapper, connection, target: DepartmentModel):
    _emit_org_changed(connection, reason="department_delete", entity="department", entity_id=str(getattr(target, "id", "")))


# Capture department membership changes (association table changes won't trigger Employee after_update)
@event.listens_for(EmployeeModel.departments, "append")
def org_employee_department_append(target: EmployeeModel, value: DepartmentModel, initiator):
    setattr(target, "_org_dept_changed", True)


@event.listens_for(EmployeeModel.departments, "remove")
def org_employee_department_remove(target: EmployeeModel, value: DepartmentModel, initiator):
    setattr(target, "_org_dept_changed", True)


@event.listens_for(Session, "after_flush")
def org_after_flush(session: Session, flush_context):
    # If any employee had departments appended/removed, emit one org_changed event.
    changed = False
    for obj in session.identity_map.values():
        if isinstance(obj, EmployeeModel) and getattr(obj, "_org_dept_changed", False):
            changed = True
            setattr(obj, "_org_dept_changed", False)

    if not changed:
        return

    conn = session.connection()
    _emit_org_changed(conn, reason="employee_departments_changed", entity="employee_departments")