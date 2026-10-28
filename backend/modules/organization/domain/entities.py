from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class EmployeeCreateEntity:
    employee_id: str
    name: str
    salary: float
    job_role: str
    manager_employee_id: Optional[str]
    departments: List[str]


@dataclass(frozen=True)
class DepartmentCreateEntity:
    name: str