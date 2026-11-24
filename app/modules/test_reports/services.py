import uuid
from datetime import UTC, datetime
from app.modules.test_reports.models import DiagnosticTestReport, ReportStatus
from app.modules.test_reports.schemas import ReportCreate, ReportRead, MyReportRead
from app.modules.test_reports.repositories import TestReportRepository
from app.modules.diagnostic_orders.repositories import DiagnosticOrderRepository
from app.core.exceptions.errors import ConflictError, ForbiddenError, NotFoundError


class TestReportService:
    def __init__(self, repo: TestReportRepository, order_repo: DiagnosticOrderRepository) -> None:
        self.repo = repo
        self.order_repo = order_repo

    async def create_report(self, data: ReportCreate, uploaded_by: uuid.UUID) -> ReportRead:
        if await self.order_repo.get_item_by_id(data.order_item_id) is None:
            raise NotFoundError("DiagnosticOrderItem", str(data.order_item_id))
        if await self.repo.get_by_order_item_id(data.order_item_id) is not None:
            raise ConflictError("TestReport", str(data.order_item_id))

        report = DiagnosticTestReport(
            order_item_id=data.order_item_id,
            uploaded_by=uploaded_by,
            file_location=data.file_location,
            report_status=ReportStatus.DRAFT,
            released_at=None,
        )

        return ReportRead.model_validate(await self.repo.add(report))

    async def get_report_by_id(self, report_id: uuid.UUID) -> ReportRead:
        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError("TestReport", str(report_id))

        return ReportRead.model_validate(report)

    async def list_reports_by_order(self, order_id: uuid.UUID) -> list[ReportRead]:
        if await self.order_repo.get_by_id(order_id) is None:
            raise NotFoundError("DiagnosticOrder", str(order_id))

        reports = await self.repo.list_by_order_id(order_id)
        return [ReportRead.model_validate(r) for r in reports]

    async def search_reports(self, status: ReportStatus | None, page: int, page_size: int) -> tuple[list[ReportRead], int]:
        reports, total = await self.repo.search(status, page, page_size)
        return [ReportRead.model_validate(r) for r in reports], total

    async def release_report(self, report_id: uuid.UUID) -> ReportRead:
        report = await self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError("TestReport", str(report_id))
        if report.report_status == ReportStatus.RELEASED:
            raise ForbiddenError("Report is already released")

        report.report_status = ReportStatus.RELEASED
        report.released_at = datetime.now(UTC)

        return ReportRead.model_validate(await self.repo.save(report))

    async def list_my_reports(self, patient_id: uuid.UUID, page: int, page_size: int) -> list[MyReportRead]:
        reports, _total = await self.repo.list_released_for_patient(patient_id, page, page_size)
        return [MyReportRead.model_validate(r) for r in reports]

    async def get_my_report_by_id(self, report_id: uuid.UUID, patient_id: uuid.UUID) -> MyReportRead:
        report = await self.repo.get_released_for_patient(report_id, patient_id)
        if report is None:
            raise NotFoundError("TestReport", str(report_id))

        return MyReportRead.model_validate(report)