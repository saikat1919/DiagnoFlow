import uuid
from fastapi import APIRouter, Query, status
from app.modules.inventory.models import MedicineBatchStatus
from app.modules.inventory.schemas import (
    AvailableStockRead, BatchCreate, BatchRead, BatchUpdate, LowStockRead,
    StockMovementCreate, StockMovementRead,
)
from app.modules.inventory.dependencies import MedicineBatchServiceDep, StockMovementServiceDep
from app.modules.users.dependencies import StaffDep, PharmacyDep, PharmacyManagerDep

inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])

@inventory_router.post("/batches/add", response_model=BatchRead, status_code=status.HTTP_201_CREATED)
async def add_batch(data: BatchCreate, service: MedicineBatchServiceDep, pharmacy: PharmacyDep) -> BatchRead:
    return await service.create_batch(data)

@inventory_router.get("/batches", response_model=list[BatchRead], status_code=status.HTTP_200_OK)
async def list_batches(
    service: MedicineBatchServiceDep,
    staff: StaffDep,
    medicine_id: uuid.UUID | None = None,
    supplier_id: uuid.UUID | None = None,
    status: MedicineBatchStatus | None = None,
    in_stock_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> list[BatchRead]:
    batches, _total = await service.search_batches(medicine_id, supplier_id, status, in_stock_only, page, page_size)
    return batches

@inventory_router.get("/batches/low-stock", response_model=list[LowStockRead], status_code=status.HTTP_200_OK)
async def low_stock(service: MedicineBatchServiceDep, staff: StaffDep) -> list[LowStockRead]:
    return await service.list_low_stock()

@inventory_router.get("/batches/expiring", response_model=list[BatchRead], status_code=status.HTTP_200_OK)
async def expiring_batches(
    service: MedicineBatchServiceDep,
    staff: StaffDep,
    days: int = Query(30, ge=0),
) -> list[BatchRead]:
    return await service.list_expiring(days)

@inventory_router.get("/batches/{batch_id}", response_model=BatchRead, status_code=status.HTTP_200_OK)
async def get_batch(batch_id: uuid.UUID, service: MedicineBatchServiceDep, staff: StaffDep) -> BatchRead:
    return await service.get_batch_by_id(batch_id)

@inventory_router.patch("/batches/{batch_id}", response_model=BatchRead, status_code=status.HTTP_200_OK)
async def update_batch(batch_id: uuid.UUID, data: BatchUpdate, service: MedicineBatchServiceDep, manager: PharmacyManagerDep) -> BatchRead:
    return await service.update_batch_status(batch_id, data)

@inventory_router.get("/stock/{medicine_id}", response_model=AvailableStockRead, status_code=status.HTTP_200_OK)
async def available_stock(medicine_id: uuid.UUID, service: MedicineBatchServiceDep, staff: StaffDep) -> AvailableStockRead:
    return await service.get_available_stock(medicine_id)

@inventory_router.post("/movements/add", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
async def add_movement(data: StockMovementCreate, service: StockMovementServiceDep, manager: PharmacyManagerDep) -> StockMovementRead:
    return await service.create_movement(data, created_by=manager.id)

@inventory_router.get("/movements/batch/{batch_id}", response_model=list[StockMovementRead], status_code=status.HTTP_200_OK)
async def list_movements(
    batch_id: uuid.UUID,
    service: StockMovementServiceDep,
    staff: StaffDep,
    page: int = 1,
    page_size: int = 20,
) -> list[StockMovementRead]:
    movements, _total = await service.list_movements_by_batch(batch_id, page, page_size)
    return movements