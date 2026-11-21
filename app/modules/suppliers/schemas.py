import uuid
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

MOBILE_NUMBER_PATTERN = r"^\+?\d{11,13}$"


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    supplier_name: Annotated[str, Field(min_length=1, max_length=255)]
    phone: Annotated[str, Field(pattern=MOBILE_NUMBER_PATTERN)]
    email: Optional[EmailStr] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v

class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    supplier_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, pattern=MOBILE_NUMBER_PATTERN)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v


class SupplierSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_name: str


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_name: str
    phone: str
    email: Optional[EmailStr]
    is_active: bool