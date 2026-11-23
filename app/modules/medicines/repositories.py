import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.medicines.models import DosageForm, Medicine

from app.modules.medicines.models import Medicine

class MedicineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, medicine: Medicine) -> Medicine:
        self.db_session.add(medicine)
        return await self.save(medicine)

    async def save(self, medicine: Medicine) -> Medicine:
        await self.db_session.flush()
        await self.db_session.refresh(medicine)
        return medicine

    async def get_by_id(self, medicine_id: uuid.UUID) -> Medicine | None:
        return await self.db_session.get(Medicine, medicine_id)

    async def get_by_ids(self, medicine_ids: list[uuid.UUID]) -> list[Medicine]:
        stmt = select(Medicine).where(Medicine.id.in_(medicine_ids))
        return list((await self.db_session.scalars(stmt)).all())

    async def get_by_identity(
            self, brand_name: str, strength: str, dosage_form: DosageForm
    ) -> Medicine | None:
        stmt = select(Medicine).where(
            func.lower(Medicine.brand_name) == brand_name.lower(),
            func.lower(Medicine.strength) == strength.lower(),
            Medicine.dosage_form == dosage_form,
        )
        return await self.db_session.scalar(stmt)

    async def search(
            self,
            q: str | None,
            dosage_form: DosageForm | None,
            active_only: bool,
            page: int,
            page_size: int,
    ) -> tuple[list[Medicine], int]:
        base = select(Medicine)
        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(
                    Medicine.brand_name.ilike(pattern),
                    Medicine.generic_name.ilike(pattern),
                )
            )
        if dosage_form is not None:
            base = base.where(Medicine.dosage_form == dosage_form)
        if active_only:
            base = base.where(Medicine.is_active.is_(True))
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(Medicine.brand_name, Medicine.strength, Medicine.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0