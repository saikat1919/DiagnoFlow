import uuid
import enum
from datetime import date
from sqlalchemy import (String, ForeignKey, Integer,
                        Text, Date, Enum,
                        CheckConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin
from app.modules.patients.models import Patient
from app.modules.medicines.models import Medicine


class PrescriptionStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_DISPENSED = "partially_dispensed"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"


class DispenseStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_DISPENSED = "partially_dispensed"
    DISPENSED = "dispensed"
    NOT_AVAILABLE = "not_available"


class Prescription(Base, TimeStampMixin):
    __tablename__ = 'prescriptions'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('patients.id'),
        index=True,
    )
    prescriber_name: Mapped[str] = mapped_column(String(255))
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id'),
    )
    prescription_date: Mapped[date] = mapped_column(Date)
    file_location: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(
            PrescriptionStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=PrescriptionStatus.PENDING,
        server_default=PrescriptionStatus.PENDING.value,
        index=True
    )

    patient: Mapped[Patient] = relationship(lazy="joined")
    items: Mapped[list["PrescriptionItem"]] = relationship(
        back_populates="prescription",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class PrescriptionItem(Base, TimeStampMixin):
    __tablename__ = 'prescription_items'
    __table_args__ = (
        CheckConstraint(
            "quantity_prescribed > 0",
            name="quantity_prescribed_more_than_zero"
        ),
        CheckConstraint(
            "quantity_delivered >= 0",
            name="quantity_delivered_zero_or_more"
        ),
        CheckConstraint(
            "quantity_delivered <= quantity_prescribed",
            name="quantity_delivered_within_prescribed"
        ),
        CheckConstraint(
            "(dispense_status IN ('pending', 'not_available') "
            "AND quantity_delivered = 0) "
            "OR (dispense_status = 'partially_dispensed' "
            "AND quantity_delivered > 0 "
            "AND quantity_delivered < quantity_prescribed) "
            "OR (dispense_status = 'dispensed' "
            "AND quantity_delivered = quantity_prescribed)",
            name="dispense_status_matches_quantity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('prescriptions.id', ondelete='CASCADE'),
        index=True
    )
    medicine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('medicines.id'),
        nullable=True
    )
    medicine_name: Mapped[str] = mapped_column(String(255))
    strength: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_prescribed: Mapped[int] = mapped_column(Integer)
    quantity_delivered: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    dispense_status: Mapped[DispenseStatus] = mapped_column(
        Enum(
            DispenseStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=DispenseStatus.PENDING,
        server_default=DispenseStatus.PENDING.value
    )

    prescription: Mapped[Prescription] = relationship(back_populates="items")
    medicine: Mapped[Medicine | None] = relationship(lazy="joined")