from sqlalchemy.orm import Session

from backend.modules.projects.application.services import ProjectsService
from backend.modules.projects.infrastructure.repository import SQLAlchemyProjectsRepository


class ProjectsFacade:
    def __init__(self, db: Session):
        self.service = ProjectsService(SQLAlchemyProjectsRepository(db))

    def create_project(self, dto):
        return self.service.create_project(dto)

    def list_projects(self):
        return self.service.list_projects()

    def get_project(self, project_id: int):
        return self.service.get_project(project_id)

    def update_project(self, project_id: int, dto):
        return self.service.update_project(project_id, dto)

    def update_task(self, project_id: int, task_id: int, dto):
        return self.service.update_task(project_id, task_id, dto)

    def delete_project(self, project_id: int):
        return self.service.delete_project(project_id)

    def create_task(self, project_id: int, dto):
        return self.service.create_task(project_id, dto)

    def list_tasks(self, project_id: int):
        return self.service.list_tasks(project_id)

    def delete_task(self, project_id: int, task_id: int):
        return self.service.delete_task(project_id, task_id)

    def simulate(self, project_id: int):
        return self.service.simulate(project_id)
