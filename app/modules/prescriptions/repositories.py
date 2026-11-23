import uuid
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.prescriptions.models import Prescription, PrescriptionItem, PrescriptionStatus


class PrescriptionRepository:
    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def add(self, prescription: Prescription) -> Prescription:
        self.db_session.add(prescription)
        return await self.save(prescription)

    async def save(self, prescription: Prescription) -> Prescription:
        await self.db_session.flush()
        await self.db_session.refresh(prescription)
        return prescription

    async def get_by_id(self, prescription_id: uuid.UUID) -> Prescription | None:
        return await self.db_session.get(Prescription, prescription_id)

    async def get_for_update(self, prescription_id: uuid.UUID) -> Prescription | None:
        stmt = (
            select(Prescription).where(Prescription.id == prescription_id)
            .with_for_update(of=Prescription)
        )
        return await self.db_session.scalar(stmt)

    async def get_for_patient(self, prescription_id: uuid.UUID, patient_id: uuid.UUID) -> Prescription | None:
        stmt = select(Prescription).where(Prescription.id == prescription_id, Prescription.patient_id == patient_id)
        return await self.db_session.scalar(stmt)

    async def get_item_by_id(self, item_id: uuid.UUID) -> PrescriptionItem | None:
        return await self.db_session.get(PrescriptionItem, item_id)

    async def search(
            self,
            q: str | None,
            patient_id: uuid.UUID | None,
            status: PrescriptionStatus | None,
            date_from: date | None,
            date_to: date | None,
            page: int,
            page_size: int
    ) -> tuple[list[Prescription], int]:
        base = select(Prescription)
        if q:
            pattern = f"%{q}%"
            base = base.where(Prescription.prescriber_name.ilike(pattern))
        if patient_id is not None:
            base = base.where(Prescription.patient_id == patient_id)
        if status is not None:
            base = base.where(Prescription.status == status)
        if date_from is not None:
            base = base.where(Prescription.prescription_date >= date_from)
        if date_to is not None:
            base = base.where(Prescription.prescription_date <= date_to)
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )

        stmt = (
            base.order_by(
                Prescription.prescription_date.desc(),
                Prescription.created_at.desc(),
                Prescription.id
            ).offset((page - 1) * page_size).limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0