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


class ProjectUpdateDTO(BaseModel):
    """Partial update: omitted fields are left unchanged."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    start_date: Optional[date] = None
    deadline: Optional[date] = None
    resource_employee_ids: Optional[List[str]] = None


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
        check_pert(self.optimistic, self.most_likely, self.pessimistic)
        return self


def check_pert(optimistic, most_likely, pessimistic) -> None:
    present = [e is not None for e in (optimistic, most_likely, pessimistic)]
    if any(present) and not all(present):
        raise ValueError("PERT requires optimistic, most_likely and pessimistic together")
    if all(present) and not (optimistic <= most_likely <= pessimistic):
        raise ValueError("PERT estimates must satisfy optimistic <= most_likely <= pessimistic")


class TaskUpdateDTO(BaseModel):
    """Partial update: omitted fields are left unchanged. Send all three PERT estimates as null to remove them."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    duration_days: Optional[float] = Field(default=None, gt=0, le=3650)
    optimistic: Optional[float] = Field(default=None, gt=0)
    most_likely: Optional[float] = Field(default=None, gt=0)
    pessimistic: Optional[float] = Field(default=None, gt=0)
    predecessor_task_ids: Optional[List[int]] = None
    resource_employee_ids: Optional[List[str]] = None


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
