from datetime import date, datetime

from pydantic import BaseModel


# Patient Schemas
class PatientCreate(BaseModel):
    """Patient creation request"""
    name: str
    species: str
    breed: str
    birthdate: date
    sex: str
    weight: float | None = None
    owner_info: dict[str, str]
    medical_history: dict = {}


class PatientUpdate(BaseModel):
    """Patient update request"""
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    birthdate: date | None = None
    sex: str | None = None
    weight: float | None = None
    owner_info: dict[str, str] | None = None
    medical_history: dict | None = None


class PatientResponse(BaseModel):
    """Patient response"""
    patient_id: str
    name: str
    species: str
    breed: str
    birthdate: date
    sex: str
    weight: float | None
    owner_info: dict[str, str]
    medical_history: dict
    created_by: str
    assigned_to: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        orm_mode = True


class PatientListResponse(BaseModel):
    """Patient list response"""
    patients: list[PatientResponse]
    total: int
    page: int
    limit: int
