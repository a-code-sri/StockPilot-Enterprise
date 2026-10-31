from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Table, UniqueConstraint, event
from sqlalchemy.orm import Session, object_session, relationship

from backend.core.database.base import Base
from backend.core.time import utcnow
from backend.outbox.repository import emit_event

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class EmployeeModel(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    # Business-facing employee id
    employee_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False, index=True)
    salary = Column(Numeric(14, 2), nullable=False)
    job_role = Column(String, nullable=False, index=True)
    # Self-referential manager FK (internal DB id)
    manager_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    manager = relationship("EmployeeModel", remote_side=[id], backref="subordinates", foreign_keys=[manager_id])
    departments = relationship("DepartmentModel", secondary=employee_departments, lazy="selectin")

    __table_args__ = (
        CheckConstraint("salary >= 0", name="ck_employee_salary_non_negative"),
        UniqueConstraint("employee_id", name="uq_employee_employee_id"),
    )


# ---------------- analytics events ----------------

_ORG_CHANGED_FLAG = "org_changed_pending"


def _emit_org_changed(connection, *, reason: str) -> None:
    emit_event(
        connection,
        module="organization",
        event_type="org_changed",
        aggregate_type="org",
        aggregate_id="org",
        payload={"reason": reason, "timestamp": utcnow().isoformat()},
    )


def _mark(target) -> None:
    session = object_session(target)
    if session is not None:
        session.info[_ORG_CHANGED_FLAG] = True


# Row-level changes and membership changes (which don't fire mapper events) all
# just set a flag; one org_changed event is emitted per flush. The organization
# snapshot is rebuilt from scratch, so one event per transaction is enough.
for _model in (EmployeeModel, DepartmentModel):
    for _evt in ("after_insert", "after_update", "after_delete"):
        event.listen(_model, _evt, lambda mapper, connection, target: _mark(target))

event.listen(EmployeeModel.departments, "append", lambda target, value, initiator: _mark(target))
event.listen(EmployeeModel.departments, "remove", lambda target, value, initiator: _mark(target))


@event.listens_for(Session, "after_flush")
def _org_after_flush(session: Session, flush_context) -> None:
    if session.info.pop(_ORG_CHANGED_FLAG, False):
        _emit_org_changed(session.connection(), reason="organization_changed")
