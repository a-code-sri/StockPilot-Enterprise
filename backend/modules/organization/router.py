from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database.adapter import DatabaseAdapter
from backend.core.rbac.dependencies import require_permission
from backend.modules.organization.facade import OrganizationFacade
from backend.modules.organization.application.dtos import (
    DepartmentCreateDTO,
    DepartmentResponseDTO,
    EmployeeCreateDTO,
    EmployeeResponseDTO,
)

router = APIRouter()

# ---------- Departments ----------

@router.post("/departments", response_model=DepartmentResponseDTO)
def create_department(
    dto: DepartmentCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization.write")),
):
    facade = OrganizationFacade(db)
    return facade.create_department(dto)

@router.get("/departments", response_model=list[DepartmentResponseDTO])
def list_departments(
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization.read")),
):
    facade = OrganizationFacade(db)
    return facade.list_departments()

# ---------- Employees ----------

@router.post("/employees", response_model=EmployeeResponseDTO)
def create_employee(
    dto: EmployeeCreateDTO,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization.write")),
):
    facade = OrganizationFacade(db)
    emp = facade.create_employee(dto)

    # Map ORM -> response shape (manager_employee_id + departments list)
    manager_employee_id = emp.manager.employee_id if emp.manager else None
    return {
        "id": emp.id,
        "employee_id": emp.employee_id,
        "name": emp.name,
        "salary": emp.salary,
        "job_role": emp.job_role,
        "manager_employee_id": manager_employee_id,
        "departments": [d.name for d in emp.departments],
        "created_at": emp.created_at,
    }

@router.get("/employees", response_model=list[EmployeeResponseDTO])
def search_employees(
    q: str | None = None,
    department: str | None = None,
    manager_employee_id: str | None = None,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization.read")),
):
    facade = OrganizationFacade(db)
    rows = facade.search_employees(q=q, department=department, manager_employee_id=manager_employee_id)

    result = []
    for emp in rows:
        result.append({
            "id": emp.id,
            "employee_id": emp.employee_id,
            "name": emp.name,
            "salary": emp.salary,
            "job_role": emp.job_role,
            "manager_employee_id": emp.manager.employee_id if emp.manager else None,
            "departments": [d.name for d in emp.departments],
            "created_at": emp.created_at,
        })
    return result

@router.delete("/employees/{employee_id}")
def delete_employee(
    employee_id: str,
    db: Session = Depends(DatabaseAdapter.get_db),
    user=Depends(require_permission("organization.write")),
):
    facade = OrganizationFacade(db)
    facade.delete_employee(employee_id)
    return {"message": "Employee deleted"}