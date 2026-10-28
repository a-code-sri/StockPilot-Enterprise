from abc import ABC, abstractmethod
from typing import Optional, List


class OrganizationRepositoryInterface(ABC):

    # Departments
    @abstractmethod
    def create_department(self, name: str):
        pass

    @abstractmethod
    def list_departments(self):
        pass

    @abstractmethod
    def get_department_by_name(self, name: str):
        pass

    # Employees
    @abstractmethod
    def create_employee(
        self,
        employee_id: str,
        name: str,
        salary: float,
        job_role: str,
        manager_id: Optional[int],
        department_ids: List[int],
    ):
        pass

    @abstractmethod
    def delete_employee(self, employee_db_id: int):
        pass

    @abstractmethod
    def get_employee_by_employee_id(self, employee_id: str):
        pass

    @abstractmethod
    def get_employee_by_db_id(self, employee_db_id: int):
        pass

    @abstractmethod
    def search_employees(
        self,
        q: Optional[str],
        department: Optional[str],
        manager_employee_id: Optional[str],
    ):
        pass