from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class ProjectCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    start_date: date
    deadline: date
    resource_employee_ids: List[str] = []


class ProjectListDTO(BaseModel):
    id: int
    title: str
    start_date: date
    deadline: date
    created_at: datetime
    resource_employee_ids: List[str]

    class Config:
        from_attributes = True


class ProjectDetailDTO(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_date: date
    deadline: date
    created_at: datetime
    resource_employee_ids: List[str]

    class Config:
        from_attributes = True


class TaskCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None

    duration_days: float = Field(gt=0)

    optimistic: Optional[float] = Field(default=None, gt=0)
    most_likely: Optional[float] = Field(default=None, gt=0)
    pessimistic: Optional[float] = Field(default=None, gt=0)

    predecessor_task_ids: List[int] = []
    resource_employee_ids: List[str] = []


class TaskDTO(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    duration_days: float
    optimistic: Optional[float]
    most_likely: Optional[float]
    pessimistic: Optional[float]
    predecessor_task_ids: List[int]
    resource_employee_ids: List[str]
    created_at: datetime

    class Config:
        from_attributes = True