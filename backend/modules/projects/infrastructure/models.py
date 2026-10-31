from sqlalchemy import CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, UniqueConstraint, event

from sqlalchemy.orm import relationship

from backend.core.database.base import Base
from backend.core.time import utcnow
from backend.outbox.repository import emit_event

# project_id <-> employees.employee_id (business id)
project_resources = Table(
    "project_resources",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("employee_id", String, ForeignKey("employees.employee_id", ondelete="RESTRICT"), primary_key=True),
)

task_resources = Table(
    "task_resources",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("employee_id", String, ForeignKey("employees.employee_id", ondelete="RESTRICT"), primary_key=True),
)

task_predecessors = Table(
    "task_predecessors",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("predecessor_id", Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    start_date = Column(Date, nullable=False)
    deadline = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    tasks = relationship("ProjectTaskModel", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    resources = relationship("EmployeeModel", secondary=project_resources, lazy="selectin", viewonly=True)

    __table_args__ = (
        UniqueConstraint("title", name="uq_projects_title"),
        CheckConstraint("deadline >= start_date", name="ck_project_deadline_after_start"),
    )


class ProjectTaskModel(Base):
    __tablename__ = "project_tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    duration_days = Column(Float, nullable=False)  # CPM duration (fallback)
    optimistic = Column(Float, nullable=True)       # PERT estimates (optional, all-or-none)
    most_likely = Column(Float, nullable=True)
    pessimistic = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    project = relationship("ProjectModel", back_populates="tasks")
    predecessors = relationship(
        "ProjectTaskModel",
        secondary=task_predecessors,
        primaryjoin=id == task_predecessors.c.task_id,
        secondaryjoin=id == task_predecessors.c.predecessor_id,
        lazy="selectin",
    )
    resources = relationship("EmployeeModel", secondary=task_resources, lazy="selectin", viewonly=True)

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="ck_task_duration_positive"),
        CheckConstraint(
            "(optimistic IS NULL AND most_likely IS NULL AND pessimistic IS NULL) OR "
            "(optimistic IS NOT NULL AND most_likely IS NOT NULL AND pessimistic IS NOT NULL)",
            name="ck_task_pert_all_or_none",
        ),
        CheckConstraint(
            "(optimistic IS NULL) OR (optimistic <= most_likely AND most_likely <= pessimistic)",
            name="ck_task_pert_order",
        ),
    )


def emit_projects_changed(connection, *, reason: str, project_id: int | None) -> None:
    emit_event(
        connection,
        module="projects",
        event_type="projects_changed",
        aggregate_type="project",
        aggregate_id=str(project_id or 0),
        payload={"reason": reason, "project_id": project_id, "timestamp": utcnow().isoformat()},
    )


@event.listens_for(ProjectModel, "after_insert")
def _project_insert(mapper, connection, target):
    emit_projects_changed(connection, reason="project_insert", project_id=target.id)


@event.listens_for(ProjectModel, "after_update")
def _project_update(mapper, connection, target):
    emit_projects_changed(connection, reason="project_update", project_id=target.id)


@event.listens_for(ProjectModel, "after_delete")
def _project_delete(mapper, connection, target):
    emit_projects_changed(connection, reason="project_delete", project_id=target.id)


@event.listens_for(ProjectTaskModel, "after_insert")
def _task_insert(mapper, connection, target):
    emit_projects_changed(connection, reason="task_insert", project_id=target.project_id)


@event.listens_for(ProjectTaskModel, "after_update")
def _task_update(mapper, connection, target):
    emit_projects_changed(connection, reason="task_update", project_id=target.project_id)


@event.listens_for(ProjectTaskModel, "after_delete")
def _task_delete(mapper, connection, target):
    emit_projects_changed(connection, reason="task_delete", project_id=target.project_id)
