import uuid
from decimal import Decimal
from sqlalchemy import String, Boolean, ForeignKey, Numeric
from app.db.base import Base, TimeStampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Department(Base, TimeStampMixin):
    __tablename__ = 'departments'
    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(length=255),
        unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    tests: Mapped[list["TestCatalogue"]] = relationship(back_populates="department")


class TestCatalogue(Base, TimeStampMixin):
    __tablename__ = "test_catalogue"

    test_code: Mapped[str] = mapped_column(
        String(length=20),
        primary_key=True,
    )
    test_name: Mapped[str] = mapped_column(
        String(length=255),
        index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id"), index=True
    )
    department: Mapped[Department] = relationship(
        back_populates="tests", lazy="joined"
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0
    )
    expected_delivery_time: Mapped[str] = mapped_column(
        String(length=255)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )



