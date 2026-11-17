import enum
import uuid
from sqlalchemy import String, Sequence, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimeStampMixin


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

patient_no_seq = Sequence("patient_no_seq", start=1)

class Patient(Base, TimeStampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    patient_no: Mapped[str] = mapped_column(
        String(length=30),
        unique=True,
        index=True
    )
    patient_name: Mapped[str] = mapped_column(
        String(length=255)
    )
    sex: Mapped[Sex] = mapped_column(
        Enum(
            Sex,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        )
    )
    age: Mapped[int] = mapped_column(Integer())
    phone_number: Mapped[str] = mapped_column(
        String(length=30),
        unique=True,
        index=True
    )
    user: Mapped["User | None"] = relationship(back_populates="patient", uselist=False)
