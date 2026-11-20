import uuid
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.diagnostic_test_catalogue.models import Department


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=255)]

class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)

class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool



class TestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    test_code: Annotated[str, Field(min_length=1, max_length=20)]
    test_name: Annotated[str, Field(min_length=1, max_length=255)]
    department_name: Annotated[Department, Field(min_length=1, max_length=255)]
    price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    expected_delivery_time: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("test_code")
    @classmethod
    def validate_test_code(cls, value: str) -> str:
        return value.upper()

class TestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    test_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    department_name: Optional[Department] = Field(default=None, min_length=1, max_length=255)
    price: Optional[Decimal] = Field(default=None, ge=0)
    expected_delivery_time: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)

class TestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_code: str
    test_name: str

class TestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_code: str
    test_name: str
    department_name: DepartmentRead
    price: Decimal
    expected_delivery_time: str
    is_active: bool