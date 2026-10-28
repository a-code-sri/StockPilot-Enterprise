from typing import Optional
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from backend.modules.organization.domain.interfaces import OrganizationRepositoryInterface

class OrganizationService:
    def __init__(self, repo: OrganizationRepositoryInterface):
        self.repo = repo

    # Departments
    def create_department(self, name: str):
        try:
            return self.repo.create_department(name=name.strip())
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department already exists."
            )

    def list_departments(self):
        return self.repo.list_departments()

    # Employees
    def create_employee(self, dto):
        # manager constraint: cannot be their own manager
        if dto.manager_employee_id and dto.manager_employee_id == dto.employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee cannot be their own manager."
            )

        # manager must exist (if provided)
        manager_id: Optional[int] = None
        if dto.manager_employee_id:
            manager = self.repo.get_employee_by_employee_id(dto.manager_employee_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Manager with employee_id '{dto.manager_employee_id}' does not exist."
                )
            manager_id = manager.id

        # departments must exist
        dept_ids = []
        for dept_name in dto.departments:
            dept = self.repo.get_department_by_name(dept_name)
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department '{dept_name}' does not exist. Create it first."
                )
            dept_ids.append(dept.id)

        try:
            return self.repo.create_employee(
                employee_id=dto.employee_id.strip(),
                name=dto.name.strip(),
                salary=float(dto.salary),
                job_role=dto.job_role.strip(),
                manager_id=manager_id,
                department_ids=dept_ids,
            )
        except IntegrityError as e:
            # likely duplicate employee_id
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error: employee_id must be unique and salary must be non-negative."
            )

    def delete_employee(self, employee_id: str):
        emp = self.repo.get_employee_by_employee_id(employee_id)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")
        self.repo.delete_employee(emp.id)

    def search_employees(self, q: Optional[str], department: Optional[str], manager_employee_id: Optional[str]):
        return self.repo.search_employees(q=q, department=department, manager_employee_id=manager_employee_id)