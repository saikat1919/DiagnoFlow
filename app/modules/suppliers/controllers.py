import uuid
from fastapi import APIRouter, status
from app.modules.suppliers.schemas import SupplierCreate, SupplierRead, SupplierUpdate
from app.modules.suppliers.dependencies import SupplierServiceDep
from app.modules.users.dependencies import StaffDep, PharmacyManagerDep

supplier_router = APIRouter(prefix="/suppliers", tags=["suppliers"])

@supplier_router.post("/add", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def add_supplier(data: SupplierCreate, service: SupplierServiceDep, manager: PharmacyManagerDep) -> SupplierRead:
    return await service.create_supplier(data)

@supplier_router.get("", response_model=list[SupplierRead], status_code=status.HTTP_200_OK)
async def list_suppliers(
    service: SupplierServiceDep,
    staff: StaffDep,
    q: str | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> list[SupplierRead]:
    suppliers, _total = await service.search_suppliers(q, active_only, page, page_size)
    return suppliers

@supplier_router.get("/{supplier_id}", response_model=SupplierRead, status_code=status.HTTP_200_OK)
async def get_supplier(supplier_id: uuid.UUID, service: SupplierServiceDep, staff: StaffDep) -> SupplierRead:
    return await service.get_supplier_by_id(supplier_id)

@supplier_router.patch("/{supplier_id}", response_model=SupplierRead, status_code=status.HTTP_200_OK)
async def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate, service: SupplierServiceDep, manager: PharmacyManagerDep) -> SupplierRead:
    return await service.update_supplier(supplier_id, data)