import uuid
from decimal import Decimal
from datetime import datetime, date
from typing import Annotated, Optional
from pydantic import (BaseModel, ConfigDict, Field,
                      model_validator, AliasPath)
from app.modules.sales.models import PaymentMethod, PaymentStatus
from app.modules.patients.schemas import PatientSummary
from app.modules.inventory.schemas import BatchSummary


class SaleItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medicine_id: uuid.UUID
    quantity: Annotated[int, Field(gt=0)]
    batch_id: Optional[uuid.UUID] = None

class SaleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: Optional[uuid.UUID] = None
    prescription_id: Optional[uuid.UUID] = None
    items: Annotated[list[SaleItemCreate], Field(min_length=1)]
    discount: Annotated[Decimal, Field(default=0,ge=0, max_digits=12, decimal_places=2)]
    payment_method: Optional[PaymentMethod] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING

    @model_validator(mode="after")
    def check_rules(self):
        if self.prescription_id is not None and self.patient_id is None:
            raise ValueError("A sale made from a prescription needs a patient.")
        if self.payment_status == PaymentStatus.PAID and self.payment_method is None:
            raise ValueError("A paid sale needs a payment method.")
        return self

class SalePaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None

    @model_validator(mode="after")
    def paid_needs_method(self):
        if self.payment_status == PaymentStatus.PAID and self.payment_method is None:
            raise ValueError("Send the payment method when marking a sale as paid.")
        return self

class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch: BatchSummary
    quantity: int
    unit_price: Decimal
    line_total: Decimal

class DailyTotalRead(BaseModel):
    sale_date: date
    sale_count: int
    total_amount: Decimal
    paid_amount: Decimal

class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sale_no: str
    patient: Optional[PatientSummary]
    prescription_id: Optional[uuid.UUID]
    sold_by: uuid.UUID
    sale_date: datetime
    subtotal: Decimal
    discount: Decimal
    total_amount: Decimal
    payment_method: Optional[PaymentMethod]
    payment_status: PaymentStatus
    items: list[SaleItemRead]


class MySaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_name: str = Field(validation_alias=AliasPath("batch", "medicine", "brand_name"))
    strength: str = Field(validation_alias=AliasPath("batch", "medicine", "strength"))
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class MySaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sale_no: str
    sale_date: datetime
    subtotal: Decimal
    discount: Decimal
    total_amount: Decimal
    payment_method: Optional[PaymentMethod]
    payment_status: PaymentStatus
    items: list[MySaleItemRead]