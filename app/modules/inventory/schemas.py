import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import (BaseModel, ConfigDict, Field,
                      field_validator)
from app.modules.inventory.models import MedicineBatchStatus, MovementType
from app.modules.medicines.schemas import MedicineSummary
from app.modules.suppliers.schemas import SupplierSummary


MANUAL_MOVEMENT_TYPES = {
    MovementType.DAMAGED,
    MovementType.RETURNED,
    MovementType.ADJUSTED,
}


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medicine_id: uuid.UUID
    supplier_id: uuid.UUID
    batch_no: Annotated[str, Field(min_length=1 ,max_length=50)]
    expiry_date: date
    quantity_received: Annotated[int, Field(gt=0)]
    purchase_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]

    @field_validator('expiry_date')
    @classmethod
    def validate_expiry_date(cls, exp_date: date) -> Optional[date]:
        if exp_date <= date.today():
            raise ValueError('Invalid expiry date. Expiry date must be in the future.')
        return exp_date


class BatchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: MedicineBatchStatus

class BatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_no: str
    expiry_date: date
    medicine: MedicineSummary

class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medicine: MedicineSummary
    supplier: SupplierSummary
    batch_no: str
    expiry_date: date
    quantity_received: int
    quantity_in_stock: int
    purchase_price: Decimal
    received_at: datetime
    status: MedicineBatchStatus


class StockMovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    batch_id: uuid.UUID
    movement_type: MovementType
    quantity: int

    @field_validator('movement_type')
    @classmethod
    def manual_movement_validation(cls, v: MovementType) -> MovementType:
        if v not in MANUAL_MOVEMENT_TYPES:
            raise ValueError("Only damaged, returned or adjusted can be selected by the user")
        return v

    @field_validator('quantity')
    @classmethod
    def not_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Quantity cannot be zero")
        return v


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_id: uuid.UUID
    movement_type: MovementType
    quantity: int
    created_by: uuid.UUID
    created_at: datetime