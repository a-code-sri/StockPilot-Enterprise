from sqlalchemy.orm import Session
from backend.modules.organization.infrastructure.repository import SQLAlchemyOrganizationRepository
from backend.modules.organization.application.services import OrganizationService

class OrganizationFacade:
    def __init__(self, db: Session):
        repo = SQLAlchemyOrganizationRepository(db)
        self.service = OrganizationService(repo)

    def create_department(self, dto):
        return self.service.create_department(dto.name)

    def list_departments(self):
        return self.service.list_departments()

    def create_employee(self, dto):
        return self.service.create_employee(dto)

    def delete_employee(self, employee_id: str):
        return self.service.delete_employee(employee_id)

    def search_employees(self, q=None, department=None, manager_employee_id=None):
        return self.service.search_employees(q=q, department=department, manager_employee_id=manager_employee_id)