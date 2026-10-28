from sqlalchemy.orm import Session
from backend.modules.projects.infrastructure.repository import SQLAlchemyProjectsRepository
from backend.modules.projects.application.services import ProjectsService


class ProjectsFacade:
    def __init__(self, db: Session):
        repo = SQLAlchemyProjectsRepository(db)
        self.service = ProjectsService(repo)

    def create_project(self, dto):
        return self.service.create_project(dto)

    def list_projects(self):
        return self.service.list_projects()

    def get_project(self, project_id: int):
        return self.service.get_project(project_id)

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