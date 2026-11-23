import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.sales.models import Sale, PaymentStatus

class SalesRepository:
    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def add(self, sale: Sale) -> Sale:
        self.db_session.add(sale)
        return await self.save(sale)

    async def save(self, sale: Sale) -> Sale:
        await self.db_session.flush()
        await self.db_session.refresh(sale)
        return sale

    async def get_by_id(self, sale_id: uuid.UUID) -> Sale | None:
        return await self.db_session.get(Sale, sale_id)

    async def get_by_sale_no(self, sale_no: str) -> Sale | None:
        stmt = select(Sale).where(Sale.sale_no == sale_no)
        return await self.db_session.scalar(stmt)

    async def get_for_patient(self, sale_id: uuid.UUID, patient_id: uuid.UUID) -> Sale | None:
        stmt = select(Sale).where(Sale.id == sale_id, Sale.patient_id == patient_id)
        return await self.db_session.scalar(stmt)

    async def search(
            self,
            q: str | None,
            patient_id: uuid.UUID | None,
            sold_by: uuid.UUID | None,
            payment_status: PaymentStatus | None,
            date_from: date | None,
            date_to: date | None,
            page: int,
            page_size: int
    ) -> tuple[list[Sale], int]:
        base = select(Sale)
        if q:
            pattern = f"%{q}%"
            base = base.where(Sale.sale_no.ilike(pattern))
        if patient_id is not None:
            base = base.where(Sale.patient_id == patient_id)
        if sold_by is not None:
            base = base.where(Sale.sold_by == sold_by)
        if payment_status is not None:
            base = base.where(Sale.payment_status == payment_status)
        if date_from is not None:
            base = base.where(cast(Sale.sale_date, Date) >= date_from)
        if date_to is not None:
            base = base.where(cast(Sale.sale_date, Date) <= date_to)

        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )

        stmt = (
            base.order_by(Sale.sale_date.desc(), Sale.id)
            .offset((page - 1) * page_size).limit(page_size)
        )

        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0

    async def daily_totals(
            self, date_from: date, date_to: date
    ) -> list[tuple[date, int, Decimal, Decimal]]:
        day = cast(Sale.sale_date, Date)
        paid = func.coalesce(
            func.sum(Sale.total_amount).filter(Sale.payment_status == PaymentStatus.PAID), 0
        )
        stmt = (
            select(day, func.count(Sale.id), func.sum(Sale.total_amount), paid)
            .where(day >= date_from, day <= date_to)
            .group_by(day)
            .order_by(day)
        )
        return [tuple(row) for row in (await self.db_session.execute(stmt)).all()]