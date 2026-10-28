from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission

from backend.modules.projects.facade import ProjectsFacade
from backend.modules.projects.application.dtos import (
    ProjectCreateDTO, ProjectListDTO, ProjectDetailDTO,
    TaskCreateDTO, TaskDTO
)

router = APIRouter()


# ---------------- Projects ----------------

@router.post("/", response_model=ProjectDetailDTO)
def create_project(
    dto: ProjectCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.write")),
):
    facade = ProjectsFacade(db)
    p = facade.create_project(dto)
    # Attach resources list
    resources = facade.service.repo.get_project_resources(p.id)
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "start_date": p.start_date,
        "deadline": p.deadline,
        "created_at": p.created_at,
        "resource_employee_ids": resources,
    }


@router.get("/", response_model=list[ProjectListDTO])
def list_projects(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    facade = ProjectsFacade(db)
    rows = facade.list_projects()
    out = []
    for p in rows:
        out.append({
            "id": p.id,
            "title": p.title,
            "start_date": p.start_date,
            "deadline": p.deadline,
            "created_at": p.created_at,
            "resource_employee_ids": facade.service.repo.get_project_resources(p.id),
        })
    return out


@router.get("/{project_id}", response_model=ProjectDetailDTO)
def get_project(
    project_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    facade = ProjectsFacade(db)
    p = facade.get_project(project_id)
    resources = facade.service.repo.get_project_resources(p.id)
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "start_date": p.start_date,
        "deadline": p.deadline,
        "created_at": p.created_at,
        "resource_employee_ids": resources,
    }


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.write")),
):
    facade = ProjectsFacade(db)
    facade.delete_project(project_id)
    return {"message": "Project deleted"}


# ---------------- Tasks ----------------

@router.post("/{project_id}/tasks", response_model=TaskDTO)
def create_task(
    project_id: int,
    dto: TaskCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.write")),
):
    facade = ProjectsFacade(db)
    t = facade.create_task(project_id, dto)
    return {
        "id": t.id,
        "project_id": t.project_id,
        "name": t.name,
        "description": t.description,
        "duration_days": t.duration_days,
        "optimistic": t.optimistic,
        "most_likely": t.most_likely,
        "pessimistic": t.pessimistic,
        "predecessor_task_ids": [p.id for p in (t.predecessors or [])],
        "resource_employee_ids": [e.employee_id for e in (t.resources or [])],
        "created_at": t.created_at,
    }


@router.get("/{project_id}/tasks", response_model=list[TaskDTO])
def list_tasks(
    project_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    facade = ProjectsFacade(db)
    tasks = facade.list_tasks(project_id)
    out = []
    for t in tasks:
        out.append({
            "id": t.id,
            "project_id": t.project_id,
            "name": t.name,
            "description": t.description,
            "duration_days": t.duration_days,
            "optimistic": t.optimistic,
            "most_likely": t.most_likely,
            "pessimistic": t.pessimistic,
            "predecessor_task_ids": [p.id for p in (t.predecessors or [])],
            "resource_employee_ids": [e.employee_id for e in (t.resources or [])],
            "created_at": t.created_at,
        })
    return out


@router.delete("/{project_id}/tasks/{task_id}")
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.write")),
):
    facade = ProjectsFacade(db)
    facade.delete_task(project_id, task_id)
    return {"message": "Task deleted"}


# ---------------- Simulation ----------------

@router.post("/{project_id}/simulate")
def simulate(
    project_id: int,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("projects.read")),
):
    facade = ProjectsFacade(db)
    return facade.simulate(project_id)