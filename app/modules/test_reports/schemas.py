import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.modules.test_reports.models import ReportStatus


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_item_id: uuid.UUID
    uploaded_by: uuid.UUID
    report_status: ReportStatus
    released_at: datetime | None
    created_at: datetime


class MyReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_item_id: uuid.UUID
    released_at: datetime | None