import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.diagnostic_orders.models import DiagnosticOrder, DiagnosticOrderItem
from app.modules.test_reports.models import DiagnosticTestReport, ReportStatus

class TestReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, report: DiagnosticTestReport) -> DiagnosticTestReport:
        self.db_session.add(report)
        return await self.save(report)

    async def save(self, report: DiagnosticTestReport) -> DiagnosticTestReport:
        await self.db_session.flush()
        await self.db_session.refresh(report)
        return report

    async def get_by_id(self, report_id: uuid.UUID) -> DiagnosticTestReport | None:
        return await self.db_session.get(DiagnosticTestReport, report_id)

    async def get_by_order_item_id(
            self, order_item_id: uuid.UUID
    ) -> DiagnosticTestReport | None:
        stmt = select(DiagnosticTestReport).where(
            DiagnosticTestReport.order_item_id == order_item_id
        )
        return await self.db_session.scalar(stmt)

    async def list_by_order_id(self, order_id: uuid.UUID) -> list[DiagnosticTestReport]:
        stmt = (
            select(DiagnosticTestReport)
            .join(DiagnosticOrderItem,
                  DiagnosticOrderItem.id == DiagnosticTestReport.order_item_id)
            .where(DiagnosticOrderItem.order_id == order_id)
            .order_by(DiagnosticTestReport.created_at)
        )
        return list((await self.db_session.scalars(stmt)).all())

    async def search(
            self, status: ReportStatus | None, page: int, page_size: int
    ) -> tuple[list[DiagnosticTestReport], int]:
        base = select(DiagnosticTestReport)
        if status is not None:
            base = base.where(DiagnosticTestReport.report_status == status)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(DiagnosticTestReport.created_at.desc(), DiagnosticTestReport.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0

    def _released_for_patient(self, patient_id: uuid.UUID):
        return (
            select(DiagnosticTestReport)
            .join(DiagnosticOrderItem,
                  DiagnosticOrderItem.id == DiagnosticTestReport.order_item_id)
            .join(DiagnosticOrder, DiagnosticOrder.id == DiagnosticOrderItem.order_id)
            .where(
                DiagnosticOrder.patient_id == patient_id,
                DiagnosticTestReport.report_status == ReportStatus.RELEASED,
            )
        )

    async def list_released_for_patient(
            self, patient_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[DiagnosticTestReport], int]:
        base = self._released_for_patient(patient_id)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(DiagnosticTestReport.released_at.desc(), DiagnosticTestReport.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0

    async def get_released_for_patient(
            self, report_id: uuid.UUID, patient_id: uuid.UUID
    ) -> DiagnosticTestReport | None:
        stmt = self._released_for_patient(patient_id).where(
            DiagnosticTestReport.id == report_id
        )
        return await self.db_session.scalar(stmt)
