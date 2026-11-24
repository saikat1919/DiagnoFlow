from fastapi import APIRouter, status, Depends
from typing import Annotated
from app.modules.users.dependencies import StaffDep
from app.core.exceptions.errors import ForbiddenError
from app.modules.patients.services import PatientService
from app.modules.patients.schemas import PatientCreate, PatientRead
from app.modules.patients.dependencies import PatientServiceDep, PatientRepositoryDep
from app.modules.users.dependencies import AdminDep, CurrentUserDep
from app.modules.users.models import Role

patient_router = APIRouter(prefix="/patients", tags=["patients"])

@patient_router.post("/add", response_model=PatientCreate, status_code=status.HTTP_201_CREATED)
async def add_patient(data: PatientCreate, service: PatientServiceDep, staff: StaffDep) -> PatientRead:
    return await service.create_patient(data)

@patient_router.get("", response_model=list[PatientRead])
async def list_patients(
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: PatientServiceDep = ...,
    staff: StaffDep = ...,
) -> list[PatientRead]:
    patients, _total = await service.search_patients(q, page, page_size)
    return patients

@patient_router.get("/patient/me", response_model=PatientRead, status_code=status.HTTP_200_OK)
async def me_patient(user: CurrentUserDep, service: PatientServiceDep) -> PatientRead:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own record")

    return await service.get_patient_by_id(user.patient_id)