import uuid
from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.modules.users.models import Role, STAFF_ROLES


MOBILE_NUMBER_PATTERN = r"^\+?\d{11,13}$"


class CreateUserStaff(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    mobile_number: str = Field(min_length=11, max_length=14)
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role

    @field_validator("role")
    @classmethod
    def check_staff_role(cls, value: Role) -> Role:
        if value not in STAFF_ROLES:
            raise ValueError("Role must be a staff role.")
        return value


class PatientAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=11, max_length=14)
    password: str = Field(min_length=8, max_length=128)

class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    mobile_number: str | None = Field(default=None, pattern=MOBILE_NUMBER_PATTERN)
    email: EmailStr | None = None
    is_active: bool | None = None

class ReadUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    mobile_number: str
    email: EmailStr | None
    role: Role
    is_active: bool
    patient_id: uuid.UUID | None