from fastapi import APIRouter, status, Depends
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from app.modules.patients.services import PatientService
from app.modules.patients.schemas import PatientCreate, PatientRead
from app.modules.patients.dependencies import PatientServiceDep, PatientRepositoryDep
from app.modules.users.dependencies import AdminDep

patient_router = APIRouter(prefix="/patients", tags=["patients"])

@patient_router.post("/add", response_model=PatientCreate, status_code=status.HTTP_201_CREATED)
async def add_patient(data: PatientCreate, service: PatientServiceDep, admin: AdminDep) -> PatientRead:
    return await service.create_patient(data)

# @patient_router.get("/patient/me", response_model=PatientRead, status_code=status.HTTP_200_OK)
# async def me_patient()