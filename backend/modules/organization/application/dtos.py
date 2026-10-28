from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DepartmentCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)

class DepartmentResponseDTO(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class EmployeeCreateDTO(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    salary: float = Field(ge=0)
    job_role: str = Field(min_length=1, max_length=200)
    manager_employee_id: Optional[str] = None
    departments: List[str] = []

class EmployeeResponseDTO(BaseModel):
    id: int
    employee_id: str
    name: str
    salary: float
    job_role: str
    manager_employee_id: Optional[str]
    departments: List[str]
    created_at: datetime

    class Config:
        from_attributes = True