import uuid
from app.modules.users.models import User
from app.modules.users.schemas import PatientAccountCreate
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientRead, PatientCreate
from app.modules.patients.repositories import PatientRepository
from app.core.exceptions.errors import ConflictError, NotFoundError


class PatientService:
    def __init__(self, repo: PatientRepository) -> None:
        self.repo = repo

    async def create_patient(self, data: PatientCreate) -> PatientRead:
        if await self.repo.get_by_phone(data.phone_number):
            raise ConflictError("Patient", data.phone_number)

        patient = Patient(
            patient_no=await self.repo.next_patient_no(),
            patient_first_name=data.patient_first_name,
            patient_last_name=data.patient_last_name,
            sex=data.sex,
            age=data.age,
            phone_number=data.phone_number
        )

        return PatientRead.model_validate(await self.repo.add(patient))

    async def get_patient_by_id(self, patient_id: uuid.UUID) -> PatientRead:
        patient = await self.repo.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Patient", str(patient_id))

        return PatientRead.model_validate(patient)

    async def search_patients(self, q: str | None, page: int, page_size: int) -> tuple[list[PatientRead], int]:
        patients, total = await self.repo.search(q, page, page_size)
        return [PatientRead.model_validate(p) for p in patients], total
