import uuid
from fastapi import APIRouter, status
from app.modules.medicines.models import DosageForm
from app.modules.medicines.schemas import MedicineCreate, MedicineRead, MedicineUpdate
from app.modules.medicines.dependencies import MedicineServiceDep
from app.modules.users.dependencies import StaffDep, PharmacyDep, CurrentUserDep

medicine_router = APIRouter(prefix="/medicines", tags=["medicines"])

@medicine_router.post("/add", response_model=MedicineRead, status_code=status.HTTP_201_CREATED)
async def add_medicine(data: MedicineCreate, service: MedicineServiceDep, pharmacy: PharmacyDep) -> MedicineRead:
    return await service.create_medicine(data)

@medicine_router.get("", response_model=list[MedicineRead], status_code=status.HTTP_200_OK)
async def list_medicines(
    service: MedicineServiceDep,
    user: CurrentUserDep,
    q: str | None = None,
    dosage_form: DosageForm | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> list[MedicineRead]:
    medicines, _total = await service.search_medicines(q, dosage_form, active_only, page, page_size)
    return medicines

@medicine_router.get("/{medicine_id}", response_model=MedicineRead, status_code=status.HTTP_200_OK)
async def get_medicine(medicine_id: uuid.UUID, service: MedicineServiceDep, user: CurrentUserDep) -> MedicineRead:
    return await service.get_medicine_by_id(medicine_id)

@medicine_router.patch("/{medicine_id}", response_model=MedicineRead, status_code=status.HTTP_200_OK)
async def update_medicine(medicine_id: uuid.UUID, data: MedicineUpdate, service: MedicineServiceDep, pharmacy: PharmacyDep) -> MedicineRead:
    return await service.update_medicine(medicine_id, data)