import uuid
from datetime import datetime, date
import enum
from decimal import Decimal
from sqlalchemy import (String, ForeignKey,text,
                        DateTime, func, Enum,
                        Numeric, Date, Integer,
                        CheckConstraint, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin
from app.modules.suppliers.models import Supplier
from app.modules.medicines.models import Medicine


class STATUS(str, enum.Enum):
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"

class PurchaseOrder(Base, TimeStampMixin):
    __tablename__ = 'purchase_orders'
    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="total_amount_zero_or_more"
        ),
        CheckConstraint(
            "(status = 'received') = (delivered_at IS NOT NULL)",
            name="delivered_at_set_when_received"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    purchase_no: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        server_default=text(
            "'PO-' || lpad(nextval('purchase_order_seq')::text, 6, '0')"
        )
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('suppliers.id')
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id')
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    status: Mapped[STATUS] = mapped_column(
        Enum(
            STATUS,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=STATUS.ORDERED,
        server_default=STATUS.ORDERED.value
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=PaymentStatus.UNPAID,
        server_default=PaymentStatus.UNPAID.value
    )
    expected_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier: Mapped[Supplier] = relationship(lazy="joined")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )



class PurchaseOrderItem(Base, TimeStampMixin):
    __tablename__ = 'purchase_order_items'
    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id",
            "medicine_id",
            name="uq_purchase_order_items_order_medicine"
        ),
        CheckConstraint(
            "quantity_ordered > 0",
            name="quantity_ordered_more_than_zero"
        ),
        CheckConstraint(
            "quantity_received >= 0",
            name="quantity_received_zero_or_more"
        ),
        CheckConstraint(
            "quantity_received <= quantity_ordered",
            name="quantity_received_within_ordered"
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="unit_cost_zero_or_more"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('purchase_orders.id', ondelete='CASCADE')
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('medicines.id'), index=True
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer)
    quantity_received: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    medicine: Mapped[Medicine] = relationship(lazy="joined")