import uuid
import enum
from sqlalchemy import String, Boolean, Enum, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin


class Role(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    RECEPTIONIST = "receptionist"
    LAB_TECHNICIAN = "lab_technician"
    PHARMACIST = "pharmacist"
    PHARMACY_MANAGER = "pharmacy_manager"
    PATIENT = "patient"

STAFF_ROLES = {
    Role.RECEPTIONIST,
    Role.LAB_TECHNICIAN,
    Role.PHARMACIST,
    Role.PHARMACY_MANAGER
}

class User(Base, TimeStampMixin):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint(
            "(role = 'patient') = (patient_id IS NOT NULL)",
            name="patient_id_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(length=255))
    last_name: Mapped[str] = mapped_column(String(length=255))
    mobile_number: Mapped[str] = mapped_column(String(length=14), unique=True)
    email: Mapped[str] = mapped_column(
        String(length=255),
        unique=True,
        index=True,
        nullable=True
    )
    password: Mapped[str] = mapped_column(String(length=255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id"), unique=True, index=True, nullable=True
    )
    patient: Mapped["Patient | None"] = relationship(back_populates="user")