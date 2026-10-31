from typing import List

from sqlalchemy.orm import Session

from backend.modules.organization.infrastructure.models import EmployeeModel
from backend.modules.projects.domain.interfaces import ProjectsRepositoryInterface
from backend.modules.projects.infrastructure.models import (
    ProjectModel,
    ProjectTaskModel,
    emit_projects_changed,
    project_resources,
    task_predecessors,
    task_resources,
)


class ProjectsValidationError(ValueError):
    pass


class SQLAlchemyProjectsRepository(ProjectsRepositoryInterface):
    """Persistence only. Never commits: the service owns the transaction."""

    def __init__(self, db: Session):
        self.db = db

    # ---------------- Projects ----------------

    def add_project(self, title: str, description, start_date, deadline) -> ProjectModel:
        model = ProjectModel(title=title, description=description, start_date=start_date, deadline=deadline)
        self.db.add(model)
        self.db.flush()
        return model

    def list_projects(self):
        return self.db.query(ProjectModel).order_by(ProjectModel.created_at.desc()).all()

    def get_project(self, project_id: int):
        return self.db.get(ProjectModel, project_id)

    def delete_project(self, project) -> None:
        self.db.delete(project)
        self.db.flush()

    # ---------------- Resources ----------------

    def _validate_employees_exist(self, employee_ids: List[str]) -> None:
        if not employee_ids:
            return
        existing = {
            eid for (eid,) in self.db.query(EmployeeModel.employee_id).filter(EmployeeModel.employee_id.in_(employee_ids))
        }
        missing = [eid for eid in employee_ids if eid not in existing]
        if missing:
            raise ProjectsValidationError(f"Unknown employee id(s): {', '.join(missing)}")

    def set_project_resources(self, project_id: int, employee_ids: List[str]) -> None:
        employee_ids = list(dict.fromkeys(employee_ids))  # dedupe, keep order
        self._validate_employees_exist(employee_ids)
        self.db.execute(project_resources.delete().where(project_resources.c.project_id == project_id))
        if employee_ids:
            self.db.execute(
                project_resources.insert(), [{"project_id": project_id, "employee_id": e} for e in employee_ids]
            )
        # Association-table writes bypass ORM mapper events, so emit explicitly.
        emit_projects_changed(self.db.connection(), reason="project_resources_set", project_id=project_id)

    def get_project_resources(self, project_id: int) -> List[str]:
        rows = self.db.execute(
            project_resources.select().where(project_resources.c.project_id == project_id)
        ).fetchall()
        return [r.employee_id for r in rows]

    # ---------------- Tasks ----------------

    def add_task(self, project_id: int, fields: dict, predecessor_task_ids: List[int], resource_employee_ids: List[str]):
        resource_employee_ids = list(dict.fromkeys(resource_employee_ids))
        predecessor_task_ids = list(dict.fromkeys(predecessor_task_ids))
        self._validate_employees_exist(resource_employee_ids)

        if predecessor_task_ids:
            found = {
                tid
                for (tid,) in self.db.query(ProjectTaskModel.id).filter(
                    ProjectTaskModel.project_id == project_id, ProjectTaskModel.id.in_(predecessor_task_ids)
                )
            }
            missing = [p for p in predecessor_task_ids if p not in found]
            if missing:
                raise ProjectsValidationError(f"Predecessor task(s) not found in this project: {missing}")

        task = ProjectTaskModel(project_id=project_id, **fields)
        self.db.add(task)
        self.db.flush()

        # New tasks can only depend on existing tasks, so this can never create a cycle.
        if predecessor_task_ids:
            self.db.execute(
                task_predecessors.insert(), [{"task_id": task.id, "predecessor_id": p} for p in predecessor_task_ids]
            )
        if resource_employee_ids:
            self.db.execute(
                task_resources.insert(), [{"task_id": task.id, "employee_id": e} for e in resource_employee_ids]
            )
        return task

    def list_tasks(self, project_id: int):
        return (
            self.db.query(ProjectTaskModel)
            .filter(ProjectTaskModel.project_id == project_id)
            .order_by(ProjectTaskModel.created_at.asc(), ProjectTaskModel.id.asc())
            .all()
        )

    def get_task(self, project_id: int, task_id: int):
        return (
            self.db.query(ProjectTaskModel)
            .filter(ProjectTaskModel.project_id == project_id, ProjectTaskModel.id == task_id)
            .first()
        )

    def set_task_links(self, task, predecessor_task_ids: List[int] | None, resource_employee_ids: List[str] | None) -> None:
        """Replace a task's predecessors and/or resources (None = unchanged). Caller checks for cycles."""
        if predecessor_task_ids is not None:
            predecessor_task_ids = list(dict.fromkeys(predecessor_task_ids))
            if task.id in predecessor_task_ids:
                raise ProjectsValidationError("A task cannot depend on itself.")
            if predecessor_task_ids:
                found = {
                    tid
                    for (tid,) in self.db.query(ProjectTaskModel.id).filter(
                        ProjectTaskModel.project_id == task.project_id, ProjectTaskModel.id.in_(predecessor_task_ids)
                    )
                }
                missing = [p for p in predecessor_task_ids if p not in found]
                if missing:
                    raise ProjectsValidationError(f"Predecessor task(s) not found in this project: {missing}")
            self.db.execute(task_predecessors.delete().where(task_predecessors.c.task_id == task.id))
            if predecessor_task_ids:
                self.db.execute(
                    task_predecessors.insert(), [{"task_id": task.id, "predecessor_id": p} for p in predecessor_task_ids]
                )

        if resource_employee_ids is not None:
            resource_employee_ids = list(dict.fromkeys(resource_employee_ids))
            self._validate_employees_exist(resource_employee_ids)
            self.db.execute(task_resources.delete().where(task_resources.c.task_id == task.id))
            if resource_employee_ids:
                self.db.execute(
                    task_resources.insert(), [{"task_id": task.id, "employee_id": e} for e in resource_employee_ids]
                )

        # Link-table writes bypass ORM mapper events; emit so analytics snapshots rebuild.
        emit_projects_changed(self.db.connection(), reason="task_links_set", project_id=task.project_id)
        self.db.expire(task, ["predecessors", "resources"])

    def predecessor_map(self, project_id: int) -> dict[int, list[int]]:
        """{task_id: [predecessor ids]} for every task in the project."""
        ids = [tid for (tid,) in self.db.query(ProjectTaskModel.id).filter(ProjectTaskModel.project_id == project_id)]
        preds: dict[int, list[int]] = {tid: [] for tid in ids}
        if ids:
            rows = self.db.execute(task_predecessors.select().where(task_predecessors.c.task_id.in_(ids))).all()
            for task_id, predecessor_id in rows:
                preds[task_id].append(predecessor_id)
        return preds

    def delete_task(self, task) -> None:
        self.db.delete(task)
        self.db.flush()
