import uuid
from datetime import date
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.prescriptions.models import DispenseStatus, PrescriptionStatus
from app.modules.medicines.schemas import MedicineSummary
from app.modules.patients.schemas import PatientSummary

class PrescriptionItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medicine_name: Annotated[str, Field(min_length=1, max_length=255)]
    strength: Optional[str] = Field(default=None, max_length=50)
    instructions: Optional[str] = Field(default=None, max_length=1000)
    quantity_prescribed: Annotated[int, Field(gt=0)]

class PrescriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: uuid.UUID
    prescriber_name: Annotated[str, Field(min_length=1, max_length=255)]
    prescription_date: date
    notes: Optional[str] = Field(default=None, max_length=1000)
    items: Annotated[list[PrescriptionItemCreate], Field(min_length=1)]

    @field_validator("prescription_date")
    @classmethod
    def validate_prescription_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Prescription date can't be in the future")
        return v

class PrescriptionItemMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicine_id: uuid.UUID


class PrescriptionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medicine: Optional[MedicineSummary]
    medicine_name: str
    strength: Optional[str]
    instructions: Optional[str]
    quantity_prescribed: int
    quantity_delivered: int
    dispense_status: DispenseStatus


class PrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient: PatientSummary
    prescriber_name: str
    recorded_by: uuid.UUID
    prescription_date: date
    notes: Optional[str]
    status: PrescriptionStatus
    items: list[PrescriptionItemRead]



class MyPrescriptionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medicine_name: str
    strength: Optional[str]
    instructions: Optional[str]
    quantity_prescribed: int
    quantity_delivered: int
    dispense_status: DispenseStatus


class MyPrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prescriber_name: str
    prescription_date: date
    status: PrescriptionStatus
    items: list[MyPrescriptionItemRead]