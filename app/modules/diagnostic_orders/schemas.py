import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.diagnostic_orders.models import WorkStatus, PaymentStatus
from app.modules.diagnostic_test_catalogue.schemas import TestSummary
from app.modules.patients.schemas import PatientSummary


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    test_code: Annotated[str, Field(min_length=1, max_length=20)]

    @field_validator("test_code")
    @classmethod
    def upper_code(cls, value: str) -> str:
        return value.upper()

class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: uuid.UUID
    expected_delivery: datetime | None = None
    items: Annotated[list[OrderItemCreate], Field(min_length=1)]

    @field_validator("items")
    @classmethod
    def no_duplicate_test(cls, items: list[OrderItemCreate]) -> list[OrderItemCreate]:
        codes = [item.test_code for item in items]
        if len(codes) != len(set(codes)):
            raise ValueError("Same test is listed more than once")
        return items

class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkStatus


class OrderItemStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_status: WorkStatus


class OrderPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_status: PaymentStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    test: TestSummary
    price_at_order: Decimal
    item_status: WorkStatus

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_no: str
    patient: PatientSummary
    created_by: uuid.UUID
    order_date: datetime
    status: WorkStatus
    total_amount: Decimal
    payment_status: PaymentStatus
    expected_delivery: datetime | None
    items: list[OrderItemRead]

class MyOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    test: TestSummary
    price_at_order: Decimal
    item_status: WorkStatus

class MyOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_no: str
    order_date: datetime
    status: WorkStatus
    total_amount: Decimal
    payment_status: PaymentStatus
    expected_delivery: datetime | None
    items: list[MyOrderItemRead]