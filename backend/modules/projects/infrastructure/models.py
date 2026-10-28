from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Float, ForeignKey, Table,
    UniqueConstraint, CheckConstraint, event
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import insert

from backend.core.database.base import Base
from backend.outbox.models import AnalyticsOutbox


# --- Project resources: project_id <-> employees.employee_id (string FK)
project_resources = Table(
    "project_resources",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("employee_id", String, ForeignKey("employees.employee_id", ondelete="RESTRICT"), primary_key=True),
)

# --- Task resources: task_id <-> employees.employee_id
task_resources = Table(
    "task_resources",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("project_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("employee_id", String, ForeignKey("employees.employee_id", ondelete="RESTRICT"), primary_key=True),
)

# --- Task predecessors (many-to-many self relation)
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

    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("ProjectTaskModel", back_populates="project", cascade="all, delete-orphan")

    # resources (employee ids)
    resources = relationship(
        "EmployeeModel",
        secondary=project_resources,
        lazy="joined",
        viewonly=True,
    )

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

    # CPM duration fallback
    duration_days = Column(Float, nullable=False)

    # PERT estimates (optional)
    optimistic = Column(Float, nullable=True)
    most_likely = Column(Float, nullable=True)
    pessimistic = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ProjectModel", back_populates="tasks")

    predecessors = relationship(
        "ProjectTaskModel",
        secondary=task_predecessors,
        primaryjoin=id == task_predecessors.c.task_id,
        secondaryjoin=id == task_predecessors.c.predecessor_id,
        lazy="joined",
    )

    # resources (employee ids)
    resources = relationship(
        "EmployeeModel",
        secondary=task_resources,
        lazy="joined",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="ck_task_duration_positive"),
        CheckConstraint(
            "(optimistic IS NULL AND most_likely IS NULL AND pessimistic IS NULL) OR "
            "(optimistic IS NOT NULL AND most_likely IS NOT NULL AND pessimistic IS NOT NULL)",
            name="ck_task_pert_all_or_none"
        ),
        CheckConstraint(
            "(optimistic IS NULL) OR (optimistic <= most_likely AND most_likely <= pessimistic)",
            name="ck_task_pert_order"
        ),
    )


def _emit_projects_changed(connection, *, reason: str, project_id: int | None = None, entity: str | None = None, entity_id: str | None = None):
    payload = {
        "reason": reason,
        "project_id": project_id,
        "entity": entity,
        "entity_id": entity_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_n": 10,
    }
    connection.execute(
        insert(AnalyticsOutbox).values(
            module="projects",
            event_type="projects_changed",
            aggregate_type="projects",
            aggregate_id=str(project_id or 0),
            payload=payload,
            status="pending",
            available_at=datetime.now(timezone.utc),
        )
    )


@event.listens_for(ProjectModel, "after_insert")
def projects_after_project_insert(mapper, connection, target: ProjectModel):
    _emit_projects_changed(connection, reason="project_insert", project_id=target.id, entity="project", entity_id=str(target.id))


@event.listens_for(ProjectModel, "after_update")
def projects_after_project_update(mapper, connection, target: ProjectModel):
    _emit_projects_changed(connection, reason="project_update", project_id=target.id, entity="project", entity_id=str(target.id))


@event.listens_for(ProjectModel, "after_delete")
def projects_after_project_delete(mapper, connection, target: ProjectModel):
    _emit_projects_changed(connection, reason="project_delete", project_id=getattr(target, "id", None), entity="project", entity_id=str(getattr(target, "id", "")))


@event.listens_for(ProjectTaskModel, "after_insert")
def projects_after_task_insert(mapper, connection, target: ProjectTaskModel):
    _emit_projects_changed(connection, reason="task_insert", project_id=target.project_id, entity="task", entity_id=str(target.id))


@event.listens_for(ProjectTaskModel, "after_update")
def projects_after_task_update(mapper, connection, target: ProjectTaskModel):
    _emit_projects_changed(connection, reason="task_update", project_id=target.project_id, entity="task", entity_id=str(target.id))


@event.listens_for(ProjectTaskModel, "after_delete")
def projects_after_task_delete(mapper, connection, target: ProjectTaskModel):
    _emit_projects_changed(connection, reason="task_delete", project_id=getattr(target, "project_id", None), entity="task", entity_id=str(getattr(target, "id", "")))