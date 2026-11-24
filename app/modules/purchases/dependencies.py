from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.purchases.repositories import PurchaseOrderRepository
from app.modules.purchases.services import PurchaseOrderService
from app.modules.suppliers.dependencies import SupplierRepositoryDep
from app.modules.medicines.dependencies import MedicineRepositoryDep
from app.modules.inventory.dependencies import MedicineBatchRepositoryDep, StockMovementRepositoryDep

def get_purchase_order_repository(session: SessionDep) -> PurchaseOrderRepository:
    return PurchaseOrderRepository(session)

PurchaseOrderRepositoryDep = Annotated[PurchaseOrderRepository, Depends(get_purchase_order_repository)]

def get_purchase_order_service(
    repo: PurchaseOrderRepositoryDep,
    supplier_repo: SupplierRepositoryDep,
    medicine_repo: MedicineRepositoryDep,
    batch_repo: MedicineBatchRepositoryDep,
    movement_repo: StockMovementRepositoryDep,
) -> PurchaseOrderService:
    return PurchaseOrderService(repo, supplier_repo, medicine_repo, batch_repo, movement_repo)

PurchaseOrderServiceDep = Annotated[PurchaseOrderService, Depends(get_purchase_order_service)]