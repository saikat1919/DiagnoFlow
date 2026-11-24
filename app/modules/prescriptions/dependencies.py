from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.prescriptions.repositories import PrescriptionRepository
from app.modules.prescriptions.services import PrescriptionService
from app.modules.patients.dependencies import PatientRepositoryDep
from app.modules.patients.repositories import PatientRepository
from app.modules.medicines.dependencies import MedicineRepositoryDep
from app.modules.medicines.repositories import MedicineRepository

def get_prescription_repository(session: SessionDep) -> PrescriptionRepository:
    return PrescriptionRepository(session)

PrescriptionRepositoryDep = Annotated[PrescriptionRepository, Depends(get_prescription_repository)]

def get_prescription_service(
    repo: PrescriptionRepositoryDep,
    patient_repo: PatientRepositoryDep,
    medicine_repo: MedicineRepositoryDep,
) -> PrescriptionService:
    return PrescriptionService(repo, patient_repo, medicine_repo)

PrescriptionServiceDep = Annotated[PrescriptionService, Depends(get_prescription_service)]