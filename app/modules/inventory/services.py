import uuid
from datetime import date
from app.modules.inventory.models import MedicineBatch, StockMovement, MovementType
from app.modules.inventory.schemas import (
    AvailableStockRead, BatchCreate, BatchRead, BatchUpdate, LowStockRead,
    StockMovementCreate, StockMovementRead,
)
from app.modules.inventory.repositories import MedicineBatchRepository, StockMovementRepository
from app.modules.medicines.repositories import MedicineRepository
from app.modules.suppliers.repositories import SupplierRepository
from app.core.exceptions.errors import ConflictError, ForbiddenError, NotFoundError


class MedicineBatchService:
    def __init__(
        self,
        repo: MedicineBatchRepository,
        medicine_repo: MedicineRepository,
        supplier_repo: SupplierRepository,
    ) -> None:
        self.repo = repo
        self.medicine_repo = medicine_repo
        self.supplier_repo = supplier_repo

    async def create_batch(self, data: BatchCreate) -> BatchRead:
        medicine = await self.medicine_repo.get_by_id(data.medicine_id)
        if medicine is None:
            raise NotFoundError("Medicine", str(data.medicine_id))
        if not medicine.is_active:
            raise ForbiddenError("Medicine is not active")
        if await self.supplier_repo.get_by_id(data.supplier_id) is None:
            raise NotFoundError("Supplier", str(data.supplier_id))
        if await self.repo.get_by_identity(data.medicine_id, data.supplier_id, data.batch_no):
            raise ConflictError("MedicineBatch", data.batch_no)

        batch = MedicineBatch(
            medicine_id=data.medicine_id,
            supplier_id=data.supplier_id,
            batch_no=data.batch_no,
            expiry_date=data.expiry_date,
            quantity_received=data.quantity_received,
            quantity_in_stock=data.quantity_received,
            purchase_price=data.purchase_price,
        )

        return BatchRead.model_validate(await self.repo.add(batch))

    async def get_batch_by_id(self, batch_id: uuid.UUID) -> BatchRead:
        batch = await self.repo.get_by_id(batch_id)
        if batch is None:
            raise NotFoundError("MedicineBatch", str(batch_id))

        return BatchRead.model_validate(batch)

    async def search_batches(self, medicine_id: uuid.UUID | None, supplier_id: uuid.UUID | None, status, in_stock_only: bool, page: int, page_size: int) -> tuple[list[BatchRead], int]:
        batches, total = await self.repo.search(medicine_id, supplier_id, status, in_stock_only, page, page_size)
        return [BatchRead.model_validate(b) for b in batches], total

    async def update_batch_status(self, batch_id: uuid.UUID, data: BatchUpdate) -> BatchRead:
        batch = await self.repo.get_by_id(batch_id)
        if batch is None:
            raise NotFoundError("MedicineBatch", str(batch_id))

        batch.status = data.status

        return BatchRead.model_validate(await self.repo.save(batch))

    async def get_available_stock(self, medicine_id: uuid.UUID) -> AvailableStockRead:
        if await self.medicine_repo.get_by_id(medicine_id) is None:
            raise NotFoundError("Medicine", str(medicine_id))

        stock = await self.repo.usable_stock([medicine_id], date.today())
        return AvailableStockRead(medicine_id=medicine_id, usable_stock=stock.get(medicine_id, 0))

    async def list_low_stock(self) -> list[LowStockRead]:
        rows = await self.repo.list_low_stock(date.today())
        return [
            LowStockRead(
                medicine=medicine,
                usable_stock=total,
                reorder_level=medicine.reorder_level,
            )
            for medicine, total in rows
        ]

    async def list_expiring(self, days: int) -> list[BatchRead]:
        batches = await self.repo.list_expiring(days, date.today())
        return [BatchRead.model_validate(b) for b in batches]


class StockMovementService:
    def __init__(self, repo: StockMovementRepository, batch_repo: MedicineBatchRepository) -> None:
        self.repo = repo
        self.batch_repo = batch_repo

    async def create_movement(self, data: StockMovementCreate, created_by: uuid.UUID) -> StockMovementRead:
        batch = await self.batch_repo.get_for_update(data.batch_id)
        if batch is None:
            raise NotFoundError("MedicineBatch", str(data.batch_id))
        if data.movement_type in (MovementType.DAMAGED, MovementType.RETURNED) and data.quantity > 0:
            raise ForbiddenError("Damaged and returned quantities must be negative")

        new_stock = batch.quantity_in_stock + data.quantity
        if new_stock < 0:
            raise ForbiddenError("Not enough stock in this batch")

        batch.quantity_in_stock = new_stock
        await self.batch_repo.save(batch)

        movement = StockMovement(
            batch_id=data.batch_id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            created_by=created_by,
        )

        return StockMovementRead.model_validate(await self.repo.add(movement))

    async def list_movements_by_batch(self, batch_id: uuid.UUID, page: int, page_size: int) -> tuple[list[StockMovementRead], int]:
        if await self.batch_repo.get_by_id(batch_id) is None:
            raise NotFoundError("MedicineBatch", str(batch_id))

        movements, total = await self.repo.list_by_batch(batch_id, page, page_size)
        return [StockMovementRead.model_validate(m) for m in movements], total