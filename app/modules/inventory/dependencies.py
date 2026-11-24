from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.inventory.repositories import MedicineBatchRepository, StockMovementRepository
from app.modules.inventory.services import MedicineBatchService, StockMovementService
from app.modules.medicines.dependencies import MedicineRepositoryDep
from app.modules.medicines.repositories import MedicineRepository
from app.modules.suppliers.dependencies import SupplierRepositoryDep
from app.modules.suppliers.repositories import SupplierRepository

def get_batch_repository(session: SessionDep) -> MedicineBatchRepository:
    return MedicineBatchRepository(session)

MedicineBatchRepositoryDep = Annotated[MedicineBatchRepository, Depends(get_batch_repository)]

def get_stock_movement_repository(session: SessionDep) -> StockMovementRepository:
    return StockMovementRepository(session)

StockMovementRepositoryDep = Annotated[StockMovementRepository, Depends(get_stock_movement_repository)]

def get_batch_service(
    repo: MedicineBatchRepositoryDep,
    medicine_repo: MedicineRepositoryDep,
    supplier_repo: SupplierRepositoryDep,
) -> MedicineBatchService:
    return MedicineBatchService(repo, medicine_repo, supplier_repo)

MedicineBatchServiceDep = Annotated[MedicineBatchService, Depends(get_batch_service)]

def get_stock_movement_service(
    repo: StockMovementRepositoryDep,
    batch_repo: MedicineBatchRepositoryDep,
) -> StockMovementService:
    return StockMovementService(repo, batch_repo)

StockMovementServiceDep = Annotated[StockMovementService, Depends(get_stock_movement_service)]