import uuid
from typing import Annotated, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.patients.models import Sex


MOBILE_NUMBER_PATTERN = r"^\+?\d{11,13}$"

class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_first_name: Annotated[str, Field(min_length=1, max_length=255)]
    patient_last_name: Annotated[str, Field(min_length=1, max_length=255)]
    sex: Sex
    age: Annotated[int, Field(ge=0, description="Patient age")]
    phone_number: Annotated[str, Field(pattern=MOBILE_NUMBER_PATTERN)]

class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_first_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    patient_last_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sex: Optional[Sex] = Field(default=None)
    age: Optional[int] = Field(default=None, ge=0)
    phone_number: Optional[str] = Field(default=None, pattern=MOBILE_NUMBER_PATTERN)

class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_no: str
    patient_first_name: str
    patient_last_name: str

class PatientRead(PatientSummary):
    sex: Sex
    age: int
    patient_first_name: str
    patient_last_name: str
    phone_number: str
    created_at: datetime