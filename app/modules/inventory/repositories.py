import uuid
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from app.modules.inventory.models import MedicineBatch, MedicineBatchStatus, StockMovement
from app.modules.medicines.models import Medicine

def usable(today: date):
    return and_(
        MedicineBatch.status == MedicineBatchStatus.ACTIVE,
        MedicineBatch.expiry_date >= today,
        MedicineBatch.quantity_in_stock > 0,
    )


class MedicineBatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, batch: MedicineBatch) -> MedicineBatch:
        self.db_session.add(batch)
        return await self.save(batch)

    async def save(self, batch: MedicineBatch) -> MedicineBatch:
        await self.db_session.flush()
        await self.db_session.refresh(batch)
        return batch

    async def get_by_id(self, batch_id: uuid.UUID) -> MedicineBatch | None:
        return await self.db_session.get(MedicineBatch, batch_id)

    async def get_for_update(self, batch_id: uuid.UUID) -> MedicineBatch | None:
        stmt = (
            select(MedicineBatch)
            .where(MedicineBatch.id == batch_id)
            .with_for_update(of=MedicineBatch)
        )
        return await self.db_session.scalar(stmt)

    async def get_by_identity(
            self, medicine_id: uuid.UUID,
            supplier_id: uuid.UUID,
            batch_no: str
    ) -> MedicineBatch | None:
        stmt = select(MedicineBatch).where(
            MedicineBatch.medicine_id == medicine_id,
            MedicineBatch.supplier_id == supplier_id,
            MedicineBatch.batch_no == batch_no,
        )
        return await self.db_session.scalar(stmt)

    async def get_usable_for_update(
            self, medicine_id: uuid.UUID, today: date
    ) -> list[MedicineBatch]:
        stmt = (
            select(MedicineBatch)
            .where(MedicineBatch.medicine_id == medicine_id, usable(today))
            .order_by(MedicineBatch.expiry_date, MedicineBatch.id)
            .with_for_update(of=MedicineBatch)
        )
        return list((await self.db_session.scalars(stmt)).all())

    async def usable_stock(
            self, medicine_ids: list[uuid.UUID], today: date
    ) -> dict[uuid.UUID, int]:
        stmt = (
            select(MedicineBatch.medicine_id, func.sum(MedicineBatch.quantity_in_stock))
            .where(MedicineBatch.medicine_id.in_(medicine_ids), usable(today))
            .group_by(MedicineBatch.medicine_id)
        )
        rows = (await self.db_session.execute(stmt)).all()
        return {medicine_id: int(total) for medicine_id, total in rows}

    async def available_medicine_ids(
            self, medicine_ids: list[uuid.UUID], today: date
    ) -> set[uuid.UUID]:
        stmt = (
            select(MedicineBatch.medicine_id)
            .where(MedicineBatch.medicine_id.in_(medicine_ids), usable(today))
            .distinct()
        )
        return set((await self.db_session.scalars(stmt)).all())

    async def list_low_stock(self, today: date) -> list[tuple[Medicine, int]]:
        stock = func.coalesce(
            func.sum(MedicineBatch.quantity_in_stock).filter(usable(today)), 0
        )
        stmt = (
            select(Medicine, stock)
            .outerjoin(MedicineBatch, MedicineBatch.medicine_id == Medicine.id)
            .where(Medicine.is_active.is_(True))
            .group_by(Medicine.id)
            .having(stock <= Medicine.reorder_level)
            .order_by(Medicine.brand_name, Medicine.strength)
        )
        return [(m, int(total)) for m, total in (await self.db_session.execute(stmt)).all()]

    async def list_expiring(self, days: int, today: date) -> list[MedicineBatch]:
        stmt = (
            select(MedicineBatch)
            .where(
                usable(today),
                MedicineBatch.expiry_date <= today + timedelta(days=days),
            )
            .order_by(MedicineBatch.expiry_date, MedicineBatch.id)
        )
        return list((await self.db_session.scalars(stmt)).all())

    async def search(
            self,
            medicine_id: uuid.UUID | None,
            supplier_id: uuid.UUID | None,
            status: MedicineBatchStatus | None,
            in_stock_only: bool,
            page: int,
            page_size: int,
    ) -> tuple[list[MedicineBatch], int]:
        base = select(MedicineBatch)
        if medicine_id is not None:
            base = base.where(MedicineBatch.medicine_id == medicine_id)
        if supplier_id is not None:
            base = base.where(MedicineBatch.supplier_id == supplier_id)
        if status is not None:
            base = base.where(MedicineBatch.status == status)
        if in_stock_only:
            base = base.where(MedicineBatch.quantity_in_stock > 0)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(MedicineBatch.expiry_date, MedicineBatch.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0


class StockMovementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, movement: StockMovement) -> StockMovement:
        self.db_session.add(movement)
        await self.db_session.flush()
        await self.db_session.refresh(movement)
        return movement

    async def list_by_batch(
            self, batch_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[StockMovement], int]:
        base = select(StockMovement).where(StockMovement.batch_id == batch_id)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(StockMovement.created_at.desc(), StockMovement.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0

    async def total_for_batch(self, batch_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.batch_id == batch_id
        )
        return int(await self.db_session.scalar(stmt))