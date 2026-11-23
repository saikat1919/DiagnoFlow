import uuid
from datetime import date
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.purchases.models import PaymentStatus, PurchaseOrder
from app.modules.purchases.models import STATUS as PurchaseOrderStatus


class PurchaseOrderRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, order: PurchaseOrder) -> PurchaseOrder:
        self.db_session.add(order)
        return await self.save(order)

    async def save(self, order: PurchaseOrder) -> PurchaseOrder:
        await self.db_session.flush()
        await self.db_session.refresh(order)
        return order

    async def get_by_id(self, order_id: uuid.UUID) -> PurchaseOrder | None:
        return await self.db_session.get(PurchaseOrder, order_id)

    async def get_for_update(self, order_id: uuid.UUID) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == order_id)
            .with_for_update(of=PurchaseOrder)
        )
        return await self.db_session.scalar(stmt)

    async def get_by_purchase_no(self, purchase_no: str) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(PurchaseOrder.purchase_no == purchase_no)
        return await self.db_session.scalar(stmt)

    async def search(
        self,
        q: str | None,
        supplier_id: uuid.UUID | None,
        status: PurchaseOrderStatus | None,
        payment_status: PaymentStatus | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PurchaseOrder], int]:
        base = select(PurchaseOrder)
        if q:
            base = base.where(PurchaseOrder.purchase_no.ilike(f"%{q}%"))
        if supplier_id is not None:
            base = base.where(PurchaseOrder.supplier_id == supplier_id)
        if status is not None:
            base = base.where(PurchaseOrder.status == status)
        if payment_status is not None:
            base = base.where(PurchaseOrder.payment_status == payment_status)
        if date_from is not None:
            base = base.where(cast(PurchaseOrder.order_date, Date) >= date_from)
        if date_to is not None:
            base = base.where(cast(PurchaseOrder.order_date, Date) <= date_to)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0