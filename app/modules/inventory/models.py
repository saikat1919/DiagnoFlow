import uuid
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (String, Integer,
                        ForeignKey, Date,
                        Numeric, DateTime, Enum,
                        UniqueConstraint,
                        CheckConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin
from app.modules.medicines.models import Medicine
from app.modules.suppliers.models import Supplier

class MedicineBatchStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    DAMAGED = "damaged"
    RETURNED = "returned"


class MedicineBatch(Base, TimeStampMixin):
    __tablename__ = "medicine_batches"
    __table_args__ = (
        UniqueConstraint(
            "medicine_id",
            "supplier_id",
            "batch_no",
            name="uq_medicine_batch"
        ),
        CheckConstraint(
            "quantity_received > 0",
            name="quantity_received_more_than_zero"
        ),
        CheckConstraint(
            "quantity_in_stock >= 0",
            name="quantity_in_stock_zero_or_more"
        ),
        CheckConstraint(
            "purchase_price >= 0",
            name="purchase_price_zero_or_more"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medicines.id")
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id"), index=True
    )
    batch_no: Mapped[str] = mapped_column(String(length=50))
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    quantity_received: Mapped[int] = mapped_column(Integer)
    quantity_in_stock: Mapped[int] = mapped_column(Integer)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[MedicineBatchStatus] = mapped_column(
        Enum(
            MedicineBatchStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=MedicineBatchStatus.ACTIVE,
        server_default=MedicineBatchStatus.ACTIVE.value,
        index=True
    )
    medicine: Mapped[Medicine] = relationship(lazy="joined")
    supplier: Mapped[Supplier] = relationship(lazy="joined")

class MovementType(str, enum.Enum):
    RECEIVED = "received"
    SOLD = "sold"
    DAMAGED = "damaged"
    ADJUSTED = "adjusted"
    RETURNED = "returned"


class StockMovement(Base, TimeStampMixin):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "quantity <> 0",
            name="quantity_not_zero"
        ),
        CheckConstraint(
            "(movement_type = 'received' AND quantity > 0) "
            "OR (movement_type IN ('sold', 'damaged', 'returned') AND quantity < 0) "
            "OR (movement_type = 'adjusted')",
            name="quantity_sign_matches_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medicine_batches.id")
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(
            MovementType,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        index=True
    )
