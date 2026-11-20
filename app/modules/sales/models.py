import uuid
import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (String, ForeignKey,
                        DateTime, Numeric, text,
                        Enum, Integer, func,
                        CheckConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin
from app.modules.patients.models import Patient
from app.modules.inventory.models import MedicineBatch

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BKASH = "bkash"
    CARD = "card"
    OTHER = "other"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"

class Sale(Base, TimeStampMixin):
    __tablename__ = 'sales'
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="subtotal_zero_or_more"),
        CheckConstraint("discount >= 0", name="discount_zero_or_more"),
        CheckConstraint("discount <= subtotal", name="discount_within_subtotal"),
        CheckConstraint(
            "total_amount = subtotal - discount",
            name="total_equals_subtotal_minus_discount"
        ),
        CheckConstraint(
            "payment_status <> 'paid' OR payment_method IS NOT NULL",
            name="payment_method_required_when_paid"
        ),
        CheckConstraint(
            "prescription_id IS NULL OR patient_id IS NOT NULL",
            name="patient_required_with_prescription"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sale_no: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        server_default=text(
            "'PS-' || lpad(nextval('sale_no_seq')::text, 6, '0')"
        )
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('patients.id'), nullable=True, index=True
    )
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('prescriptions.id'), nullable=True, index=True
    )
    sold_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default=text("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        nullable=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value
    )
    patient: Mapped[Patient | None] = relationship(lazy="joined")
    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", lazy="selectin"
    )


class SaleItem(Base, TimeStampMixin):
    __tablename__ = 'sale_items'
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_more_than_zero"),
        CheckConstraint("unit_price >= 0", name="unit_price_zero_or_more"),
        CheckConstraint(
            "line_total = quantity * unit_price",
            name="line_total_equals_quantity_times_price"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sales.id', ondelete="CASCADE"), index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medicine_batches.id"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale: Mapped[Sale] = relationship(back_populates="items")
    batch: Mapped[MedicineBatch] = relationship(lazy="joined")
