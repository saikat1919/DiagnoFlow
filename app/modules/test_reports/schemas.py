import uuid
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.test_reports.models import ReportStatus


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    order_item_id: uuid.UUID
    file_location: Annotated[str, Field(min_length=1, max_length=500)]


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