from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=15)
    password: str = Field(min_length=8, max_length=100)
    address: Optional[str] = None

class LoginIn(BaseModel):
    email: str
    password: str
    role: Optional[str] = None

class ComplaintIn(BaseModel):
    location: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    priority: Literal["Low", "Medium", "High"] = "Medium"
    photo_path: Optional[str] = None

class StatusIn(BaseModel):
    status: Literal["Pending", "In Progress", "Resolved"]

class AssignmentIn(BaseModel):
    complaint_id: int
    worker_id: int

class WorkerIn(BaseModel):
    worker_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=15)
    department_id: int

class DepartmentIn(BaseModel):
    department_name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
