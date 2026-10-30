from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    start_date: date
    deadline: date
    resource_employee_ids: List[str] = []

    @model_validator(mode="after")
    def _dates(self):
        if self.deadline < self.start_date:
            raise ValueError("deadline must be on or after start_date")
        return self


class ProjectListDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_date: date
    deadline: date
    created_at: datetime
    resource_employee_ids: List[str]


class ProjectDetailDTO(ProjectListDTO):
    description: Optional[str]


class TaskCreateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)

    duration_days: float = Field(gt=0, le=3650)

    optimistic: Optional[float] = Field(default=None, gt=0)
    most_likely: Optional[float] = Field(default=None, gt=0)
    pessimistic: Optional[float] = Field(default=None, gt=0)

    predecessor_task_ids: List[int] = []
    resource_employee_ids: List[str] = []

    @model_validator(mode="after")
    def _pert(self):
        estimates = (self.optimistic, self.most_likely, self.pessimistic)
        present = [e is not None for e in estimates]
        if any(present) and not all(present):
            raise ValueError("PERT requires optimistic, most_likely and pessimistic together")
        if all(present) and not (self.optimistic <= self.most_likely <= self.pessimistic):
            raise ValueError("PERT estimates must satisfy optimistic <= most_likely <= pessimistic")
        return self


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
