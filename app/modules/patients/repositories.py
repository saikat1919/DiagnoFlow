import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.patients.models import Patient, patient_no_seq

class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def next_patient_no(self) -> str:
        number = await self.db_session.scalar(select(patient_no_seq.next_value()))
        return f"P-{number:03d}"

    async def add(self, patient: Patient) -> Patient:
        self.db_session.add(patient)
        return await self.save(patient)

    async def save(self, patient: Patient) -> Patient:
        await self.db_session.flush()
        await self.db_session.refresh(patient)
        return patient

    async def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return await self.db_session.get(Patient, patient_id)

    async def get_by_phone(self, phone_number: str) -> Patient | None:
        stmt = select(Patient).where(Patient.phone_number == phone_number)
        return await self.db_session.scalar(stmt)

    async def search(self, q: str | None, page: int, page_size: int) -> tuple[list[Patient], int]:
        base = select(Patient)
        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(
                    Patient.patient_name.ilike(pattern),
                    Patient.phone_number.ilike(pattern),
                    Patient.patient_no.ilike(pattern)
                )
            )
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(Patient.created_at.desc(), Patient.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0