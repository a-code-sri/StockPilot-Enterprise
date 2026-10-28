from dataclasses import dataclass
from datetime import date
from typing import Optional, List


@dataclass(frozen=True)
class ProjectCreateEntity:
    title: str
    description: Optional[str]
    start_date: date
    deadline: date
    resource_employee_ids: List[str]


@dataclass(frozen=True)
class TaskCreateEntity:
    name: str
    description: Optional[str]
    duration_days: float  # CPM duration (fallback)
    optimistic: Optional[float]
    most_likely: Optional[float]
    pessimistic: Optional[float]
    predecessor_task_ids: List[int]
    resource_employee_ids: List[str]