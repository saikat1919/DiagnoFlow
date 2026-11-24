from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.patients.repositories import PatientRepository
from app.modules.patients.services import PatientService

def get_patient_repository(session: SessionDep) -> PatientRepository:
    return PatientRepository(session)

PatientRepositoryDep = Annotated[PatientRepository, Depends(get_patient_repository)]

def get_patient_service(repo: PatientRepositoryDep) -> PatientService:
    return PatientService(repo)

PatientServiceDep = Annotated[PatientService, Depends(get_patient_service)]