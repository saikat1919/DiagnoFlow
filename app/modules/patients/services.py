import uuid
from app.modules.patients.models import Patient
from app.modules.patients.schemas import PatientRead, PatientCreate, PatientUpdate
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

    async def update_patient(self, patient_id: uuid.UUID, data: PatientUpdate) -> PatientRead:
        patient = await self.repo.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Patient", str(patient_id))

        updated_data = data.model_dump(exclude_unset=True)
        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        if "phone_number" in new_data:
            existing = await self.repo.get_by_phone(new_data["phone_number"])
            if existing is not None and existing.id != patient.id:
                raise ConflictError("Patient", new_data["phone_number"])

        for key, value in new_data.items():
            setattr(patient, key, value)

        return PatientRead.model_validate(await self.repo.save(patient))
