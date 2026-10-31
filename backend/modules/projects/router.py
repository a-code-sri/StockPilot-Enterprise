from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.rbac.dependencies import require_permission
from backend.modules.projects.application.dtos import (
    ProjectCreateDTO,
    ProjectDetailDTO,
    ProjectListDTO,
    ProjectUpdateDTO,
    TaskCreateDTO,
    TaskDTO,
    TaskUpdateDTO,
)
from backend.modules.projects.facade import ProjectsFacade

router = APIRouter()

can_read = require_permission("projects.read")
can_write = require_permission("projects.write")


def _project_row(p, *, detail: bool = False) -> dict:
    row = {
        "id": p.id,
        "title": p.title,
        "start_date": p.start_date,
        "deadline": p.deadline,
        "created_at": p.created_at,
        # `resources` is eager-loaded (selectin), so listing projects is not N+1.
        "resource_employee_ids": sorted(e.employee_id for e in p.resources),
    }
    if detail:
        row["description"] = p.description
    return row


def _task_row(t) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "name": t.name,
        "description": t.description,
        "duration_days": t.duration_days,
        "optimistic": t.optimistic,
        "most_likely": t.most_likely,
        "pessimistic": t.pessimistic,
        "predecessor_task_ids": sorted(p.id for p in (t.predecessors or [])),
        "resource_employee_ids": sorted(e.employee_id for e in (t.resources or [])),
        "created_at": t.created_at,
    }


# ---------------- Projects ----------------

@router.post("/", response_model=ProjectDetailDTO, status_code=201)
def create_project(dto: ProjectCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    return _project_row(ProjectsFacade(db).create_project(dto), detail=True)


@router.get("/", response_model=list[ProjectListDTO])
def list_projects(db: Session = Depends(get_db), user=Depends(can_read)):
    return [_project_row(p) for p in ProjectsFacade(db).list_projects()]


@router.get("/{project_id}", response_model=ProjectDetailDTO)
def get_project(project_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    return _project_row(ProjectsFacade(db).get_project(project_id), detail=True)


@router.put("/{project_id}", response_model=ProjectDetailDTO)
def update_project(project_id: int, dto: ProjectUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    """Change title, description, dates and/or team. Omitted fields stay as they are."""
    return _project_row(ProjectsFacade(db).update_project(project_id, dto), detail=True)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), user=Depends(can_write)):
    ProjectsFacade(db).delete_project(project_id)
    return {"message": "Project deleted"}


# ---------------- Tasks ----------------

@router.post("/{project_id}/tasks", response_model=TaskDTO, status_code=201)
def create_task(project_id: int, dto: TaskCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    return _task_row(ProjectsFacade(db).create_task(project_id, dto))


@router.get("/{project_id}/tasks", response_model=list[TaskDTO])
def list_tasks(project_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    return [_task_row(t) for t in ProjectsFacade(db).list_tasks(project_id)]


@router.put("/{project_id}/tasks/{task_id}", response_model=TaskDTO)
def update_task(
    project_id: int, task_id: int, dto: TaskUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)
):
    """Edit a task, including its predecessors and assigned people. Dependency loops are rejected."""
    return _task_row(ProjectsFacade(db).update_task(project_id, task_id, dto))


@router.delete("/{project_id}/tasks/{task_id}")
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db), user=Depends(can_write)):
    ProjectsFacade(db).delete_task(project_id, task_id)
    return {"message": "Task deleted"}


# ---------------- Simulation ----------------

@router.post("/{project_id}/simulate")
def simulate(project_id: int, db: Session = Depends(get_db), user=Depends(can_read)):
    """Runs CPM/PERT on the current task graph (read-only)."""
    return ProjectsFacade(db).simulate(project_id)
