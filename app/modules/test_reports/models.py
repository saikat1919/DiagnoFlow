import uuid
import enum
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, Enum, DateTime, CheckConstraint
from app.db.base import Base, TimeStampMixin

class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    RELEASED = "released"

class DiagnosticTestReport(Base, TimeStampMixin):
    __tablename__ = 'test_reports'
    __table_args__ = (
        CheckConstraint(
            "(report_status = 'released') = (released_at IS NOT NULL)",
            name="released_at_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("diagnostic_order_items.id"),
        unique=True,
        index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id")
    )
    file_location: Mapped[str] = mapped_column(
        String(length=500)
    )
    report_status: Mapped[ReportStatus] = mapped_column(
        Enum(
            ReportStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e]
        ),
        default=ReportStatus.DRAFT,
        server_default=ReportStatus.DRAFT.value,
        index=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

