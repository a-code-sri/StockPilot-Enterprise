from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class DepartmentResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    headcount: int = 0


class EmployeeCreateDTO(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    salary: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    job_role: str = Field(min_length=1, max_length=200)
    manager_employee_id: Optional[str] = None
    departments: List[str] = []


class EmployeeUpdateDTO(BaseModel):
    """Partial update; omitted fields are unchanged. Send manager_employee_id="" to clear the manager."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    salary: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    job_role: Optional[str] = Field(default=None, min_length=1, max_length=200)
    manager_employee_id: Optional[str] = None
    departments: Optional[List[str]] = None


class EmployeeResponseDTO(BaseModel):
    id: int
    employee_id: str
    name: str
    salary: float
    job_role: str
    manager_employee_id: Optional[str]
    departments: List[str]
    created_at: datetime
