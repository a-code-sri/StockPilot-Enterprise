from contextlib import contextmanager
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.modules.projects.analytics import to_task_inputs
from backend.modules.projects.application.dtos import check_pert
from backend.modules.projects.domain.scheduling import (
    CycleError,
    TaskInput,
    compute_schedule,
    resource_conflicts,
    topological_order,
)
from backend.modules.projects.infrastructure.repository import ProjectsValidationError


class ProjectsService:
    def __init__(self, repo):
        self.repo = repo
        self.db = repo.db

    @contextmanager
    def _atomic(self, conflict_detail: str):
        try:
            yield
            self.db.commit()
        except ProjectsValidationError as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail)
        except Exception:
            self.db.rollback()
            raise

    # ---------------- Projects ----------------

    def create_project(self, dto):
        # Project + resources commit together; invalid resources leave nothing behind.
        with self._atomic("A project with this title already exists."):
            project = self.repo.add_project(dto.title.strip(), dto.description, dto.start_date, dto.deadline)
            self.repo.set_project_resources(project.id, dto.resource_employee_ids)
        self.db.refresh(project)
        return project

    def list_projects(self):
        return self.repo.list_projects()

    def get_project(self, project_id: int):
        p = self.repo.get_project(project_id)
        if not p:
            raise HTTPException(status_code=404, detail="Project not found.")
        return p

    def update_project(self, project_id: int, dto):
        project = self.get_project(project_id)
        fields = dto.model_fields_set
        start = dto.start_date if dto.start_date else project.start_date
        deadline = dto.deadline if dto.deadline else project.deadline
        if deadline < start:
            raise HTTPException(status_code=400, detail="Deadline must be on or after the start date.")

        with self._atomic("A project with this title already exists."):
            if dto.title:
                project.title = dto.title.strip()
            if "description" in fields:
                project.description = (dto.description or "").strip() or None
            project.start_date, project.deadline = start, deadline
            self.db.flush()
            if dto.resource_employee_ids is not None:
                self.repo.set_project_resources(project.id, dto.resource_employee_ids)
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: int) -> None:
        project = self.get_project(project_id)
        with self._atomic("Project could not be deleted."):
            self.repo.delete_project(project)

    # ---------------- Tasks ----------------

    def create_task(self, project_id: int, dto):
        self.get_project(project_id)
        with self._atomic("Task violates a constraint (check PERT estimates and durations)."):
            task = self.repo.add_task(
                project_id,
                {
                    "name": dto.name.strip(),
                    "description": dto.description,
                    "duration_days": float(dto.duration_days),
                    "optimistic": dto.optimistic,
                    "most_likely": dto.most_likely,
                    "pessimistic": dto.pessimistic,
                },
                dto.predecessor_task_ids,
                dto.resource_employee_ids,
            )
        self.db.refresh(task)
        return task

    def update_task(self, project_id: int, task_id: int, dto):
        self.get_project(project_id)
        task = self.repo.get_task(project_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        fields = dto.model_fields_set

        pert_changed = bool({"optimistic", "most_likely", "pessimistic"} & fields)
        o = dto.optimistic if "optimistic" in fields else task.optimistic
        m = dto.most_likely if "most_likely" in fields else task.most_likely
        p = dto.pessimistic if "pessimistic" in fields else task.pessimistic
        try:
            check_pert(o, m, p)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if dto.predecessor_task_ids is not None:
            # The edited graph must stay acyclic (no task may end up waiting for itself).
            graph = self.repo.predecessor_map(project_id)
            graph[task.id] = [x for x in dict.fromkeys(dto.predecessor_task_ids) if x in graph]
            try:
                topological_order({tid: TaskInput(tid, "", 1, predecessor_ids=tuple(ps)) for tid, ps in graph.items()})
            except CycleError:
                raise HTTPException(
                    status_code=400, detail="Those predecessors would create a dependency loop (a task would wait for itself)."
                )

        with self._atomic("Task violates a constraint (check PERT estimates and durations)."):
            if dto.name:
                task.name = dto.name.strip()
            if "description" in fields:
                task.description = (dto.description or "").strip() or None
            if dto.duration_days:
                task.duration_days = float(dto.duration_days)
            if pert_changed:
                task.optimistic, task.most_likely, task.pessimistic = o, m, p
            self.db.flush()
            if dto.predecessor_task_ids is not None or dto.resource_employee_ids is not None:
                self.repo.set_task_links(task, dto.predecessor_task_ids, dto.resource_employee_ids)
        self.db.refresh(task)
        return task

    def list_tasks(self, project_id: int):
        self.get_project(project_id)
        return self.repo.list_tasks(project_id)

    def delete_task(self, project_id: int, task_id: int) -> None:
        self.get_project(project_id)
        task = self.repo.get_task(project_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        with self._atomic("Task could not be deleted."):
            self.repo.delete_task(task)

    # ---------------- Simulation (CPM/PERT) ----------------

    def simulate(self, project_id: int) -> dict:
        project = self.get_project(project_id)
        inputs = to_task_inputs(self.repo.list_tasks(project_id))
        available_days = (project.deadline - project.start_date).days

        try:
            sched = compute_schedule(inputs)
        except CycleError as e:
            raise HTTPException(status_code=400, detail=str(e))

        def to_date(offset_days: float) -> str:
            return (project.start_date + timedelta(days=float(offset_days))).isoformat()

        tasks_out = [
            {
                "id": t.id,
                "name": t.name,
                "expected_duration_days": sched.tasks[t.id]["duration"],
                "ES": sched.tasks[t.id]["ES"],
                "EF": sched.tasks[t.id]["EF"],
                "LS": sched.tasks[t.id]["LS"],
                "LF": sched.tasks[t.id]["LF"],
                "float": sched.tasks[t.id]["float"],
                "planned_start": to_date(sched.tasks[t.id]["ES"]),
                "planned_end": to_date(sched.tasks[t.id]["EF"]),
                "predecessor_task_ids": list(t.predecessor_ids),
                "resource_employee_ids": list(t.resource_ids),
            }
            for t in inputs
        ]

        return {
            "project_id": project_id,
            "project_duration_days": sched.duration_days,
            "project_std_dev_days": round(sched.std_dev_days, 4),
            "critical_path_task_ids": sched.critical_path,
            "tasks": sorted(tasks_out, key=lambda x: (x["ES"], x["id"])),
            "resource_conflicts": resource_conflicts(inputs, sched) if inputs else {},
            "deadline_days_remaining": available_days - sched.duration_days,
        }
