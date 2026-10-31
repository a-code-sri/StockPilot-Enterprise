from abc import ABC, abstractmethod
from typing import List


class ProjectsRepositoryInterface(ABC):
    @abstractmethod
    def add_project(self, title: str, description, start_date, deadline):
        pass

    @abstractmethod
    def list_projects(self):
        pass

    @abstractmethod
    def get_project(self, project_id: int):
        pass

    @abstractmethod
    def delete_project(self, project):
        pass

    @abstractmethod
    def set_project_resources(self, project_id: int, employee_ids: List[str]):
        pass

    @abstractmethod
    def get_project_resources(self, project_id: int) -> List[str]:
        pass

    @abstractmethod
    def add_task(self, project_id: int, fields: dict, predecessor_task_ids: List[int], resource_employee_ids: List[str]):
        pass

    @abstractmethod
    def list_tasks(self, project_id: int):
        pass

    @abstractmethod
    def get_task(self, project_id: int, task_id: int):
        pass

    @abstractmethod
    def delete_task(self, task):
        pass
