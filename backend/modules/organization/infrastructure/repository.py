from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.modules.organization.domain.interfaces import OrganizationRepositoryInterface
from backend.modules.organization.infrastructure.models import (
    EmployeeModel,
    DepartmentModel,
)

class SQLAlchemyOrganizationRepository(OrganizationRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    # Departments
    def create_department(self, name: str):
        dept = DepartmentModel(name=name)
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def list_departments(self):
        return self.db.query(DepartmentModel).order_by(DepartmentModel.name.asc()).all()

    def get_department_by_name(self, name: str):
        return self.db.query(DepartmentModel).filter(DepartmentModel.name == name).first()

    # Employees
    def create_employee(
        self,
        employee_id: str,
        name: str,
        salary: float,
        job_role: str,
        manager_id: Optional[int],
        department_ids: List[int],
    ):
        employee = EmployeeModel(
            employee_id=employee_id,
            name=name,
            salary=salary,
            job_role=job_role,
            manager_id=manager_id,
        )

        if department_ids:
            depts = self.db.query(DepartmentModel).filter(DepartmentModel.id.in_(department_ids)).all()
            employee.departments = depts

        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def delete_employee(self, employee_db_id: int):
        emp = self.db.query(EmployeeModel).filter(EmployeeModel.id == employee_db_id).first()
        if emp:
            self.db.delete(emp)
            self.db.commit()

    def get_employee_by_employee_id(self, employee_id: str):
        return self.db.query(EmployeeModel).filter(EmployeeModel.employee_id == employee_id).first()

    def get_employee_by_db_id(self, employee_db_id: int):
        return self.db.query(EmployeeModel).filter(EmployeeModel.id == employee_db_id).first()

    def search_employees(
        self,
        q: Optional[str],
        department: Optional[str],
        manager_employee_id: Optional[str],
    ):
        query = self.db.query(EmployeeModel)

        if q:
            like = f"%{q}%"
            query = query.filter(
                (EmployeeModel.employee_id.ilike(like)) |
                (EmployeeModel.name.ilike(like)) |
                (EmployeeModel.job_role.ilike(like))
            )

        if manager_employee_id:
            manager = self.get_employee_by_employee_id(manager_employee_id)
            if manager:
                query = query.filter(EmployeeModel.manager_id == manager.id)
            else:
                # no matches if manager doesn't exist
                return []

        if department:
            query = query.join(EmployeeModel.departments).filter(DepartmentModel.name == department)

        return query.order_by(EmployeeModel.created_at.desc()).all()