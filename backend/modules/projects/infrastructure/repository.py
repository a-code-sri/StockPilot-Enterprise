from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.modules.projects.domain.interfaces import ProjectsRepositoryInterface
from backend.modules.projects.infrastructure.models import (
    ProjectModel, ProjectTaskModel,
    project_resources, task_resources, task_predecessors
)

# Import EmployeeModel only for validation queries (optional but gives better errors)
from backend.modules.organization.infrastructure.models import EmployeeModel

# NEW (needed): outbox enqueue for association-table changes
from backend.outbox.repository import enqueue_event


class SQLAlchemyProjectsRepository(ProjectsRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    # ---------------- Projects ----------------
    def create_project(self, title: str, description, start_date, deadline):
        model = ProjectModel(
            title=title,
            description=description,
            start_date=start_date,
            deadline=deadline,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def list_projects(self):
        return self.db.query(ProjectModel).order_by(ProjectModel.created_at.desc()).all()

    def get_project(self, project_id: int):
        return self.db.query(ProjectModel).filter(ProjectModel.id == project_id).first()

    def delete_project(self, project_id: int):
        model = self.get_project(project_id)
        if model:
            self.db.delete(model)
            self.db.commit()

    # ---------------- Resources ----------------
    def _validate_employees_exist(self, employee_ids: List[str]):
        if not employee_ids:
            return
        existing = self.db.query(EmployeeModel.employee_id).filter(EmployeeModel.employee_id.in_(employee_ids)).all()
        existing_set = {x[0] for x in existing}
        missing = [eid for eid in employee_ids if eid not in existing_set]
        if missing:
            raise ValueError(f"Invalid employee_id(s) (not found): {missing}")

    def set_project_resources(self, project_id: int, employee_ids: List[str]):
        """
        IMPORTANT for Phase 1:
        - This modifies association table via raw SQL -> ORM hooks won't fire.
        - We must emit an outbox event here so project analytics snapshots rebuild.
        """
        self._validate_employees_exist(employee_ids)

        # clear and re-insert
        self.db.execute(project_resources.delete().where(project_resources.c.project_id == project_id))
        for eid in employee_ids:
            self.db.execute(project_resources.insert().values(project_id=project_id, employee_id=eid))

        # NEW: emit projects_changed for analytics (same transaction as resource changes)
        enqueue_event(
            self.db,
            module="projects",
            event_type="projects_changed",
            aggregate_type="project",
            aggregate_id=str(project_id),
            payload={
                "reason": "project_resources_set",
                "project_id": project_id,
                "resource_employee_ids_count": len(employee_ids or []),
            },
        )

        self.db.commit()

    def get_project_resources(self, project_id: int) -> List[str]:
        rows = self.db.execute(
            project_resources.select().where(project_resources.c.project_id == project_id)
        ).fetchall()
        return [r.employee_id for r in rows]

    # ---------------- Tasks ----------------
    def create_task(
        self,
        project_id: int,
        name: str,
        description,
        duration_days: float,
        optimistic,
        most_likely,
        pessimistic,
        predecessor_task_ids: List[int],
        resource_employee_ids: List[str],
    ):
        """
        IMPORTANT for Phase 1:
        - Ensure task row + predecessors + resources are created in ONE transaction.
        - This avoids partial writes and ensures the outbox event emitted by the ORM
          hook (ProjectTaskModel after_insert) reflects the final committed state.
        """
        self._validate_employees_exist(resource_employee_ids)

        try:
            task = ProjectTaskModel(
                project_id=project_id,
                name=name,
                description=description,
                duration_days=duration_days,
                optimistic=optimistic,
                most_likely=most_likely,
                pessimistic=pessimistic,
            )
            self.db.add(task)
            self.db.flush()  # get task.id without committing

            # predecessors
            if predecessor_task_ids:
                # ensure predecessors belong to same project
                preds = self.db.query(ProjectTaskModel).filter(
                    ProjectTaskModel.project_id == project_id,
                    ProjectTaskModel.id.in_(predecessor_task_ids)
                ).all()
                pred_ids = {p.id for p in preds}
                missing = [pid for pid in predecessor_task_ids if pid not in pred_ids]
                if missing:
                    raise ValueError(f"Invalid predecessor task id(s): {missing}")

                for pid in predecessor_task_ids:
                    self.db.execute(task_predecessors.insert().values(task_id=task.id, predecessor_id=pid))

            # resources
            for eid in resource_employee_ids or []:
                self.db.execute(task_resources.insert().values(task_id=task.id, employee_id=eid))

            # No explicit enqueue_event needed here if you already have ORM hook on ProjectTaskModel after_insert.
            # Because everything is in one commit now, that one outbox event will see predecessors/resources too.

            self.db.commit()
            self.db.refresh(task)
            return task

        except Exception:
            self.db.rollback()
            raise

    def list_tasks(self, project_id: int):
        return self.db.query(ProjectTaskModel).filter(
            ProjectTaskModel.project_id == project_id
        ).order_by(ProjectTaskModel.created_at.asc()).all()

    def delete_task(self, project_id: int, task_id: int):
        task = self.db.query(ProjectTaskModel).filter(
            ProjectTaskModel.project_id == project_id,
            ProjectTaskModel.id == task_id
        ).first()
        if task:
            self.db.delete(task)
            self.db.commit()