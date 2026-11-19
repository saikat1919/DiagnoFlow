import uuid
import enum
from decimal import Decimal
from sqlalchemy import (String, Enum, Text,
                        Numeric, Integer, Boolean,
                        UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimeStampMixin

class DosageForm(str, enum.Enum):
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"
    INJECTION = "injection"
    CREAM = "cream"
    DROPS = "drops"
    OINTMENT = "ointment"
    OTHER = "other"


class Medicine(Base, TimeStampMixin):
    __tablename__ = 'medicines'
    __table_args__ = (
        UniqueConstraint(
            "brand_name",
            "strength",
            "dosage_form",
            name="uq_medicines_brand_strength_form"
        ),
        CheckConstraint(
            "reorder_level >= 0", name="reorder_level_zero_or_more"
        ),
        CheckConstraint(
            "selling_price >= 0", name="selling_price_zero_or_more"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_name: Mapped[str] = mapped_column(String(length=250))
    generic_name: Mapped[str] = mapped_column(String(length=250), index=True)
    strength: Mapped[str] = mapped_column(String(length=50))
    dosage_form: Mapped[DosageForm] = mapped_column(
        Enum(
            DosageForm,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        )
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reorder_level: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)