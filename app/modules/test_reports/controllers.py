import uuid
from fastapi import APIRouter, status, File, Form, UploadFile
from fastapi.responses import FileResponse
from app.modules.test_reports.models import ReportStatus
from app.modules.test_reports.schemas import ReportCreate, ReportRead, MyReportRead
from app.modules.test_reports.dependencies import TestReportServiceDep
from app.modules.users.dependencies import CurrentUserDep, StaffDep, LabDep
from app.modules.users.models import Role
from app.core.exceptions.errors import ForbiddenError

test_report_router = APIRouter(prefix="/test-reports", tags=["test reports"])

@test_report_router.post("/add", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def add_report(data: ReportCreate, service: TestReportServiceDep, lab: LabDep) -> ReportRead:
    return await service.create_report(data, uploaded_by=lab.id)

@test_report_router.post("/upload", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def upload_report(
    service: TestReportServiceDep,
    lab: LabDep,
    order_item_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
) -> ReportRead:
    return await service.create_report_upload(
        order_item_id, await file.read(), file.filename or "report", lab.id
    )

@test_report_router.post("/{report_id}/upload", response_model=ReportRead, status_code=status.HTTP_200_OK)
async def replace_report_upload(
    report_id: uuid.UUID,
    service: TestReportServiceDep,
    lab: LabDep,
    file: UploadFile = File(...),
) -> ReportRead:
    return await service.replace_report_file(report_id, await file.read(), file.filename or "report")

@test_report_router.get("/me/{report_id}/file")
async def download_my_report_file(
    report_id: uuid.UUID,
    service: TestReportServiceDep,
    user: CurrentUserDep,
) -> FileResponse:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can download their own reports")
    path, media_type, filename = await service.get_my_report_file(report_id, user.patient_id)
    return FileResponse(path, media_type=media_type, filename=filename)


@test_report_router.get("/{report_id}/file")
async def download_report_file(
    report_id: uuid.UUID,
    service: TestReportServiceDep,
    lab: LabDep,
) -> FileResponse:
    path, media_type, filename = await service.get_report_file_for_lab(report_id)
    return FileResponse(path, media_type=media_type, filename=filename)

@test_report_router.get("", response_model=list[ReportRead], status_code=status.HTTP_200_OK)
async def list_reports(
    service: TestReportServiceDep,
    staff: StaffDep,
    status: ReportStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[ReportRead]:
    reports, _total = await service.search_reports(status, page, page_size)
    return reports

@test_report_router.get("/me", response_model=list[MyReportRead], status_code=status.HTTP_200_OK)
async def my_reports(
    service: TestReportServiceDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> list[MyReportRead]:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own reports")
    return await service.list_my_reports(user.patient_id, page, page_size)

@test_report_router.get("/me/{report_id}", response_model=MyReportRead, status_code=status.HTTP_200_OK)
async def my_report(report_id: uuid.UUID, service: TestReportServiceDep, user: CurrentUserDep) -> MyReportRead:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own reports")
    return await service.get_my_report_by_id(report_id, user.patient_id)

@test_report_router.get("/order/{order_id}", response_model=list[ReportRead], status_code=status.HTTP_200_OK)
async def reports_by_order(order_id: uuid.UUID, service: TestReportServiceDep, staff: StaffDep) -> list[ReportRead]:
    return await service.list_reports_by_order(order_id)

@test_report_router.get("/{report_id}", response_model=ReportRead, status_code=status.HTTP_200_OK)
async def get_report(report_id: uuid.UUID, service: TestReportServiceDep, staff: StaffDep) -> ReportRead:
    return await service.get_report_by_id(report_id)

@test_report_router.patch("/{report_id}/release", response_model=ReportRead, status_code=status.HTTP_200_OK)
async def release_report(report_id: uuid.UUID, service: TestReportServiceDep, lab: LabDep) -> ReportRead:
    return await service.release_report(report_id)