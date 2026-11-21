import uuid
from typing import Annotated, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.modules.medicines.models import DosageForm


class MedicineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brand_name: Annotated[str, Field(min_length=1, max_length=250)]
    generic_name: Annotated[str, Field(min_length=1, max_length=250)]
    strength: Annotated[str, Field(min_length=1, max_length=50)]
    dosage_form: DosageForm
    description: Optional[str] = Field(default=None, max_length=1000)
    selling_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    reorder_level: Annotated[int, Field(default=0, ge=0)]


class MedicineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brand_name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    generic_name: Optional[str] = Field(default=None,min_length=1, max_length=250)
    strength: Optional[str] = Field(default=None,min_length=1, max_length=50)
    dosage_form: Optional[DosageForm] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    selling_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    reorder_level: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class MedicineSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_name: str
    strength: str
    dosage_form: DosageForm

class MedicineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_name: str
    generic_name: str
    strength: str
    dosage_form: DosageForm
    description: Optional[str]
    selling_price: Decimal
    reorder_level: int
    is_active: bool

class MedicineCatalogueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_name: str
    generic_name: str
    strength: str
    dosage_form: DosageForm
    selling_price: Decimal
    available: bool