import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.diagnostic_orders.models import (DiagnosticOrder,
                                                  DiagnosticOrderItem,
                                                  PaymentStatus, WorkStatus)

class DiagnosticOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, order: DiagnosticOrder) -> DiagnosticOrder:
        self.db_session.add(order)
        return await self.save(order)

    async def save(self, order: DiagnosticOrder) -> DiagnosticOrder:
        await self.db_session.flush()
        await self.db_session.refresh(order)
        return order

    async def get_by_id(self, order_id: uuid.UUID) -> DiagnosticOrder | None:
        return await self.db_session.get(DiagnosticOrder, order_id)

    async def get_by_invoice_no(self, invoice_no: str) -> DiagnosticOrder | None:
        stmt = select(DiagnosticOrder).where(DiagnosticOrder.invoice_no == invoice_no)
        return await self.db_session.scalar(stmt)

    async def get_item_by_id(self, item_id: uuid.UUID) -> DiagnosticOrderItem | None:
        return await self.db_session.get(DiagnosticOrderItem, item_id)

    async def search(
            self,
            q: str | None,
            patient_id: uuid.UUID | None,
            status: WorkStatus | None,
            payment_status: PaymentStatus | None,
            page: int,
            page_size: int,
    ) -> tuple[list[DiagnosticOrder], int]:
        base = select(DiagnosticOrder)
        if q:
            base = base.where(DiagnosticOrder.invoice_no.ilike(f"%{q}%"))
        if patient_id is not None:
            base = base.where(DiagnosticOrder.patient_id == patient_id)
        if status is not None:
            base = base.where(DiagnosticOrder.status == status)
        if payment_status is not None:
            base = base.where(DiagnosticOrder.payment_status == payment_status)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(DiagnosticOrder.order_date.desc(), DiagnosticOrder.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0
