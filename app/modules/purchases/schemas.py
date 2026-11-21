import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.purchases.models import PaymentStatus
from app.modules.purchases.models import STATUS as PurchaseOrderStatus
from app.modules.medicines.schemas import MedicineSummary
from app.modules.suppliers.schemas import SupplierSummary

class PurchaseOrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medicine_id: uuid.UUID
    quantity_ordered: Annotated[int, Field(gt=0)]
    unit_cost: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]

class PurchaseOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    supplier_id: uuid.UUID
    expected_delivery: Optional[date] = Field(default=None)
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)

    @field_validator('expected_delivery')
    @classmethod
    def expected_delivery_validator(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError("Expected delivery date can't be in past")
        return v

    @field_validator("items")
    @classmethod
    def no_duplicate_medicines(cls, items: list[PurchaseOrderItemCreate]) -> list[PurchaseOrderItemCreate]:
        ids = [item.medicine_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Same medicine added more than once")
        return items

class ReceiveItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    purchase_order_item_id: uuid.UUID
    quantity_received: Annotated[int, Field(gt=0)]
    batch_no: Annotated[str, Field(min_length=1, max_length=50)]
    expiry_date: date

    @field_validator("expiry_date")
    @classmethod
    def expiry_date_validator(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("Expiry date must be in future")
        return v

class ReceiveDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    items: Annotated[list[ReceiveItem], Field(min_length=1)]

    @field_validator("items")
    @classmethod
    def no_duplicate_item(cls, items: list[ReceiveItem]) -> list[ReceiveItem]:
        pairs = [(item.purchase_order_item_id, item.batch_no) for item in items]
        if len(pairs) != len(set(pairs)):
            raise ValueError("Same batch number added more than once")
        return items

class PurchasePaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    payment_status: PaymentStatus

class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medicine: MedicineSummary
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal

class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_no: str
    supplier: SupplierSummary
    created_by: uuid.UUID
    order_date: datetime
    status: PurchaseOrderStatus
    total_amount: Decimal
    payment_status: PaymentStatus
    expected_delivery: Optional[date]
    delivered_at: Optional[datetime]
    items: list[PurchaseOrderItemRead]