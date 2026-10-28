from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.modules.organization.infrastructure.models import (
    EmployeeModel,
    DepartmentModel,
    employee_departments,
)


class OrganizationAnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def department_headcount(self):
        """
        Returns rows: (department_name, headcount)
        Includes departments with 0 employees as well.
        """
        rows = (
            self.db.query(
                DepartmentModel.name.label("department"),
                func.count(EmployeeModel.id).label("headcount"),
            )
            .outerjoin(employee_departments, employee_departments.c.department_id == DepartmentModel.id)
            .outerjoin(EmployeeModel, employee_departments.c.employee_db_id == EmployeeModel.id)
            .group_by(DepartmentModel.name)
            .order_by(func.count(EmployeeModel.id).desc(), DepartmentModel.name.asc())
            .all()
        )
        return [{"department": r.department, "headcount": int(r.headcount)} for r in rows]

    def get_all_salaries(self):
        rows = self.db.query(EmployeeModel.salary).all()
        return [float(r[0]) for r in rows if r[0] is not None]

    def get_top_executive(self):
        """
        "Highest employee (who does not report to anyone himself)" interpreted as:
        - employee with manager_id IS NULL
        - if multiple, pick highest salary
        """
        emp = (
            self.db.query(EmployeeModel)
            .filter(EmployeeModel.manager_id.is_(None))
            .order_by(EmployeeModel.salary.desc(), EmployeeModel.created_at.asc())
            .first()
        )
        return emp