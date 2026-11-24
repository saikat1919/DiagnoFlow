import uuid
from datetime import date
from fastapi import APIRouter, status
from app.modules.prescriptions.models import PrescriptionStatus
from app.modules.prescriptions.schemas import (
    PrescriptionCreate, PrescriptionItemMatch, PrescriptionItemRead,
    PrescriptionRead, MyPrescriptionRead,
)
from app.modules.prescriptions.dependencies import PrescriptionServiceDep
from app.modules.users.dependencies import CurrentUserDep, StaffDep, PharmacyDep
from app.modules.users.models import Role
from app.core.exceptions.errors import ForbiddenError

prescription_router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

@prescription_router.post("/add", response_model=PrescriptionRead, status_code=status.HTTP_201_CREATED)
async def add_prescription(data: PrescriptionCreate, service: PrescriptionServiceDep, staff: StaffDep) -> PrescriptionRead:
    return await service.create_prescription(data, recorded_by=staff.id)

@prescription_router.get("", response_model=list[PrescriptionRead], status_code=status.HTTP_200_OK)
async def list_prescriptions(
    service: PrescriptionServiceDep,
    staff: StaffDep,
    q: str | None = None,
    patient_id: uuid.UUID | None = None,
    status: PrescriptionStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[PrescriptionRead]:
    prescriptions, _total = await service.search_prescriptions(q, patient_id, status, date_from, date_to, page, page_size)
    return prescriptions

@prescription_router.get("/me", response_model=list[MyPrescriptionRead], status_code=status.HTTP_200_OK)
async def my_prescriptions(
    service: PrescriptionServiceDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> list[MyPrescriptionRead]:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own prescriptions")
    return await service.list_my_prescriptions(user.patient_id, page, page_size)

@prescription_router.get("/me/{prescription_id}", response_model=MyPrescriptionRead, status_code=status.HTTP_200_OK)
async def my_prescription(prescription_id: uuid.UUID, service: PrescriptionServiceDep, user: CurrentUserDep) -> MyPrescriptionRead:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own prescriptions")
    return await service.get_my_prescription_by_id(prescription_id, user.patient_id)

@prescription_router.get("/{prescription_id}", response_model=PrescriptionRead, status_code=status.HTTP_200_OK)
async def get_prescription(prescription_id: uuid.UUID, service: PrescriptionServiceDep, staff: StaffDep) -> PrescriptionRead:
    return await service.get_prescription_by_id(prescription_id)

@prescription_router.patch("/items/{item_id}/match", response_model=PrescriptionItemRead, status_code=status.HTTP_200_OK)
async def match_prescription_item(item_id: uuid.UUID, data: PrescriptionItemMatch, service: PrescriptionServiceDep, pharmacy: PharmacyDep) -> PrescriptionItemRead:
    return await service.match_item(item_id, data)

@prescription_router.patch("/items/{item_id}/not-available", response_model=PrescriptionItemRead, status_code=status.HTTP_200_OK)
async def mark_item_not_available(item_id: uuid.UUID, service: PrescriptionServiceDep, pharmacy: PharmacyDep) -> PrescriptionItemRead:
    return await service.mark_item_not_available(item_id)

@prescription_router.patch("/{prescription_id}/cancel", response_model=PrescriptionRead, status_code=status.HTTP_200_OK)
async def cancel_prescription(prescription_id: uuid.UUID, service: PrescriptionServiceDep, pharmacy: PharmacyDep) -> PrescriptionRead:
    return await service.cancel_prescription(prescription_id)