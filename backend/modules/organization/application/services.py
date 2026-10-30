from contextlib import contextmanager
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.modules.organization.domain.entities import would_create_cycle
from backend.modules.organization.domain.interfaces import OrganizationRepositoryInterface


class OrganizationService:
    def __init__(self, repo: OrganizationRepositoryInterface):
        self.repo = repo
        self.db = repo.db

    @contextmanager
    def _atomic(self, conflict_detail: str):
        """Commit on success; roll back on any error. Constraint violations (raised on
        flush or commit) become 409 Conflict with a readable message."""
        try:
            yield
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail)
        except Exception:
            self.db.rollback()
            raise

    # ---------------- Departments ----------------

    def create_department(self, name: str):
        with self._atomic("Department already exists."):
            dept = self.repo.create_department(name=name.strip())
        self.db.refresh(dept)
        return dept, 0

    def list_departments(self):
        return self.repo.list_departments_with_headcount()

    def delete_department(self, name: str) -> None:
        dept = self.repo.get_department_by_name(name)
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")
        if self.repo.department_headcount(dept.id):
            raise HTTPException(status_code=409, detail="Department still has employees. Reassign them first.")
        with self._atomic("Department is still in use."):
            self.repo.delete_department(dept)

    # ---------------- Employees ----------------

    def _require_employee(self, employee_id: str):
        emp = self.repo.get_employee_by_employee_id(employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")
        return emp

    def _resolve_departments(self, names: List[str]):
        names = [n.strip() for n in names if n.strip()]
        depts = self.repo.get_departments_by_names(names)
        missing = sorted(set(names) - {d.name for d in depts})
        if missing:
            raise HTTPException(status_code=400, detail=f"Department(s) not found: {', '.join(missing)}. Create them first.")
        return depts

    def _resolve_manager_id(self, manager_employee_id: Optional[str], employee_id: str) -> Optional[int]:
        if not manager_employee_id:
            return None
        if manager_employee_id == employee_id:
            raise HTTPException(status_code=400, detail="Employee cannot be their own manager.")
        manager = self.repo.get_employee_by_employee_id(manager_employee_id)
        if not manager:
            raise HTTPException(status_code=400, detail=f"Manager '{manager_employee_id}' does not exist.")
        return manager.id

    def create_employee(self, dto):
        employee_id = dto.employee_id.strip()
        if self.repo.get_employee_by_employee_id(employee_id):
            raise HTTPException(status_code=409, detail=f"Employee id '{employee_id}' already exists.")

        manager_id = self._resolve_manager_id(dto.manager_employee_id, employee_id)
        departments = self._resolve_departments(dto.departments)
        with self._atomic("Employee id must be unique."):
            emp = self.repo.add_employee(
                employee_id=employee_id,
                name=dto.name.strip(),
                salary=dto.salary,
                job_role=dto.job_role.strip(),
                manager_id=manager_id,
                departments=departments,
            )
        self.db.refresh(emp)
        return emp

    def update_employee(self, employee_id: str, dto):
        emp = self._require_employee(employee_id)
        fields = dto.model_fields_set

        with self._atomic("Could not update employee."):
            self._apply_update(emp, dto, fields)
        self.db.refresh(emp)
        return emp

    def _apply_update(self, emp, dto, fields) -> None:
        if "name" in fields and dto.name is not None:
            emp.name = dto.name.strip()
        if "salary" in fields and dto.salary is not None:
            emp.salary = dto.salary
        if "job_role" in fields and dto.job_role is not None:
            emp.job_role = dto.job_role.strip()
        if "manager_employee_id" in fields:
            new_manager = self._resolve_manager_id(dto.manager_employee_id, emp.employee_id)
            if would_create_cycle(emp.id, new_manager, self.repo.manager_id_of):
                raise HTTPException(status_code=400, detail="That manager would create a reporting loop.")
            emp.manager_id = new_manager
        if "departments" in fields and dto.departments is not None:
            emp.departments = self._resolve_departments(dto.departments)

    def delete_employee(self, employee_id: str) -> None:
        emp = self._require_employee(employee_id)
        with self._atomic("Employee is assigned to projects or tasks. Remove them from those resources first."):
            self.repo.delete_employee(emp)

    def search_employees(self, *, q, department, manager_employee_id, limit: int, offset: int):
        return self.repo.search_employees(
            q=q, department=department, manager_employee_id=manager_employee_id, limit=limit, offset=offset
        )
