from abc import ABC, abstractmethod
from typing import List, Optional


class OrganizationRepositoryInterface(ABC):

    @abstractmethod
    def create_department(self, name: str):
        pass

    @abstractmethod
    def list_departments_with_headcount(self):
        pass

    @abstractmethod
    def get_department_by_name(self, name: str):
        pass

    @abstractmethod
    def get_departments_by_names(self, names: List[str]):
        pass

    @abstractmethod
    def delete_department(self, department):
        pass

    @abstractmethod
    def add_employee(self, **fields):
        pass

    @abstractmethod
    def delete_employee(self, employee):
        pass

    @abstractmethod
    def get_employee_by_employee_id(self, employee_id: str):
        pass

    @abstractmethod
    def manager_id_of(self, employee_db_id: int) -> Optional[int]:
        pass

    @abstractmethod
    def search_employees(self, *, q, department, manager_employee_id, limit: int, offset: int):
        pass
