import uuid
from sqlalchemy import String, Boolean, true
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimeStampMixin


class Supplier(Base, TimeStampMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_name: Mapped[str] = mapped_column(String(length=255))
    phone: Mapped[str] = mapped_column(String(length=30), unique=True)
    email: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, server_default=true())



