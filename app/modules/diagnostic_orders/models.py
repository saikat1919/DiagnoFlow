import enum
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (String,
                        ForeignKey, DateTime,
                        Enum, Numeric,
                        UniqueConstraint, text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin
from app.modules.patients.models import Patient
from app.modules.diagnostic_test_catalogue.models import TestCatalogue


class WorkStatus(str, enum.Enum):
    REGISTERED = "registered"
    SAMPLE_COLLECTED = "sample_collected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"

class DiagnosticOrder(Base, TimeStampMixin):
    __tablename__ = "diagnostic_orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_no: Mapped[str] = mapped_column(
        String(length=30),
        unique=True,
        index=True,
        server_default=text("'DI-' || lpad(nextval('diagnostic_invoice_seq')::text, 6, '0')")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[WorkStatus] = mapped_column(
        Enum(
            WorkStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=WorkStatus.REGISTERED,
        server_default=WorkStatus.REGISTERED.value,
        index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
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
    expected_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    patient: Mapped[Patient] = relationship(lazy="joined")
    items: Mapped[list["DiagnosticOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class DiagnosticOrderItem(Base, TimeStampMixin):
    __tablename__ = "diagnostic_order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "test_code", name="order_test"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("diagnostic_orders.id", ondelete="CASCADE"), index=True
    )
    test_code: Mapped[str] = mapped_column(
        ForeignKey("test_catalogue.test_code"), index=True
    )
    price_at_order: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    item_status: Mapped[WorkStatus] = mapped_column(
        Enum(
            WorkStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=WorkStatus.REGISTERED,
        server_default=WorkStatus.REGISTERED.value,
        index=True
    )
    order: Mapped[DiagnosticOrder] = relationship(back_populates="items")
    test: Mapped[TestCatalogue] = relationship(lazy="joined")