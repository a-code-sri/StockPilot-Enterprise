from abc import ABC, abstractmethod
from typing import Optional, List


class ProjectsRepositoryInterface(ABC):
    # Projects
    @abstractmethod
    def create_project(self, title: str, description, start_date, deadline):
        pass

    @abstractmethod
    def list_projects(self):
        pass

    @abstractmethod
    def get_project(self, project_id: int):
        pass

    @abstractmethod
    def delete_project(self, project_id: int):
        pass

    # Project resources
    @abstractmethod
    def set_project_resources(self, project_id: int, employee_ids: List[str]):
        pass

    @abstractmethod
    def get_project_resources(self, project_id: int) -> List[str]:
        pass

    # Tasks
    @abstractmethod
    def create_task(
        self,
        project_id: int,
        name: str,
        description,
        duration_days: float,
        optimistic,
        most_likely,
        pessimistic,
        predecessor_task_ids: List[int],
        resource_employee_ids: List[str],
    ):
        pass

    @abstractmethod
    def list_tasks(self, project_id: int):
        pass

    @abstractmethod
    def delete_task(self, project_id: int, task_id: int):
        pass