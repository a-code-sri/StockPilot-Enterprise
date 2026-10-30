from sqlalchemy.orm import Session

from backend.modules.organization.application.services import OrganizationService
from backend.modules.organization.infrastructure.repository import SQLAlchemyOrganizationRepository


class OrganizationFacade:
    def __init__(self, db: Session):
        self.service = OrganizationService(SQLAlchemyOrganizationRepository(db))

    def create_department(self, dto):
        return self.service.create_department(dto.name)

    def list_departments(self):
        return self.service.list_departments()

    def delete_department(self, name: str):
        return self.service.delete_department(name)

    def create_employee(self, dto):
        return self.service.create_employee(dto)

    def update_employee(self, employee_id: str, dto):
        return self.service.update_employee(employee_id, dto)

    def delete_employee(self, employee_id: str):
        return self.service.delete_employee(employee_id)

    def search_employees(self, **filters):
        return self.service.search_employees(**filters)
