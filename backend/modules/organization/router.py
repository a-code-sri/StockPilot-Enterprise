from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.core.database.adapter import get_db
from backend.core.pagination import Page, page_params, set_total
from backend.core.rbac.dependencies import require_permission
from backend.modules.organization.application.dtos import (
    DepartmentCreateDTO,
    DepartmentResponseDTO,
    EmployeeCreateDTO,
    EmployeeResponseDTO,
    EmployeeUpdateDTO,
)
from backend.modules.organization.facade import OrganizationFacade

router = APIRouter()

can_read = require_permission("organization.read")
can_write = require_permission("organization.write")


def employee_row(emp) -> dict:
    return {
        "id": emp.id,
        "employee_id": emp.employee_id,
        "name": emp.name,
        "salary": float(emp.salary),
        "job_role": emp.job_role,
        "manager_employee_id": emp.manager.employee_id if emp.manager else None,
        "departments": sorted(d.name for d in emp.departments),
        "created_at": emp.created_at,
    }


def _department_row(dept, headcount: int) -> dict:
    return {"id": dept.id, "name": dept.name, "created_at": dept.created_at, "headcount": int(headcount)}


# ---------- Departments ----------

@router.post("/departments", response_model=DepartmentResponseDTO, status_code=201)
def create_department(dto: DepartmentCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    return _department_row(*OrganizationFacade(db).create_department(dto))


@router.get("/departments", response_model=list[DepartmentResponseDTO])
def list_departments(db: Session = Depends(get_db), user=Depends(can_read)):
    return [_department_row(d, n) for d, n in OrganizationFacade(db).list_departments()]


@router.delete("/departments/{name}")
def delete_department(name: str, db: Session = Depends(get_db), user=Depends(can_write)):
    OrganizationFacade(db).delete_department(name)
    return {"message": "Department deleted"}


# ---------- Employees ----------

@router.post("/employees", response_model=EmployeeResponseDTO, status_code=201)
def create_employee(dto: EmployeeCreateDTO, db: Session = Depends(get_db), user=Depends(can_write)):
    return employee_row(OrganizationFacade(db).create_employee(dto))


@router.get("/employees", response_model=list[EmployeeResponseDTO])
def search_employees(
    response: Response,
    q: Optional[str] = None,
    department: Optional[str] = None,
    manager_employee_id: Optional[str] = None,
    page: Page = Depends(page_params),
    db: Session = Depends(get_db),
    user=Depends(can_read),
):
    rows, total = OrganizationFacade(db).search_employees(
        q=q, department=department, manager_employee_id=manager_employee_id, limit=page.limit, offset=page.offset
    )
    set_total(response, total)
    return [employee_row(e) for e in rows]


@router.put("/employees/{employee_id}", response_model=EmployeeResponseDTO)
def update_employee(
    employee_id: str, dto: EmployeeUpdateDTO, db: Session = Depends(get_db), user=Depends(can_write)
):
    return employee_row(OrganizationFacade(db).update_employee(employee_id, dto))


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str, db: Session = Depends(get_db), user=Depends(can_write)):
    OrganizationFacade(db).delete_employee(employee_id)
    return {"message": "Employee deleted"}
