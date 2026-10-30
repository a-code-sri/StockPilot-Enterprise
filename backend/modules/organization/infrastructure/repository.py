from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from backend.modules.organization.domain.interfaces import OrganizationRepositoryInterface
from backend.modules.organization.infrastructure.models import DepartmentModel, EmployeeModel, employee_departments


class SQLAlchemyOrganizationRepository(OrganizationRepositoryInterface):
    """Persistence only. Never commits: the service owns the transaction."""

    def __init__(self, db: Session):
        self.db = db

    # ---------------- Departments ----------------

    def create_department(self, name: str) -> DepartmentModel:
        dept = DepartmentModel(name=name)
        self.db.add(dept)
        self.db.flush()
        return dept

    def list_departments_with_headcount(self):
        return (
            self.db.query(DepartmentModel, func.count(employee_departments.c.employee_db_id))
            .outerjoin(employee_departments, employee_departments.c.department_id == DepartmentModel.id)
            .group_by(DepartmentModel.id)
            .order_by(DepartmentModel.name.asc())
            .all()
        )

    def get_department_by_name(self, name: str) -> Optional[DepartmentModel]:
        return self.db.query(DepartmentModel).filter(DepartmentModel.name == name).first()

    def get_departments_by_names(self, names: List[str]) -> List[DepartmentModel]:
        if not names:
            return []
        return self.db.query(DepartmentModel).filter(DepartmentModel.name.in_(names)).all()

    def department_headcount(self, department_id: int) -> int:
        return (
            self.db.query(func.count())
            .select_from(employee_departments)
            .filter(employee_departments.c.department_id == department_id)
            .scalar()
        )

    def delete_department(self, department) -> None:
        self.db.delete(department)
        self.db.flush()

    # ---------------- Employees ----------------

    def add_employee(self, **fields) -> EmployeeModel:
        departments = fields.pop("departments", [])
        employee = EmployeeModel(**fields)
        employee.departments = departments
        self.db.add(employee)
        self.db.flush()
        return employee

    def delete_employee(self, employee) -> None:
        self.db.delete(employee)
        self.db.flush()

    def get_employee_by_employee_id(self, employee_id: str) -> Optional[EmployeeModel]:
        return self.db.query(EmployeeModel).filter(EmployeeModel.employee_id == employee_id).first()

    def manager_id_of(self, employee_db_id: int) -> Optional[int]:
        return self.db.query(EmployeeModel.manager_id).filter(EmployeeModel.id == employee_db_id).scalar()

    def search_employees(self, *, q, department, manager_employee_id, limit: int, offset: int):
        query = self.db.query(EmployeeModel)

        if q:
            like = f"%{q}%"
            query = query.filter(
                EmployeeModel.employee_id.ilike(like) | EmployeeModel.name.ilike(like) | EmployeeModel.job_role.ilike(like)
            )

        if manager_employee_id:
            manager = self.get_employee_by_employee_id(manager_employee_id)
            if not manager:
                return [], 0
            query = query.filter(EmployeeModel.manager_id == manager.id)

        if department:
            query = query.join(EmployeeModel.departments).filter(DepartmentModel.name == department)

        total = query.count()
        rows = (
            query.options(selectinload(EmployeeModel.manager), selectinload(EmployeeModel.departments))
            .order_by(EmployeeModel.created_at.desc(), EmployeeModel.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return rows, total
