from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.sales.repositories import SalesRepository
from app.modules.sales.services import SaleService
from app.modules.medicines.dependencies import MedicineRepositoryDep
from app.modules.inventory.dependencies import MedicineBatchRepositoryDep, StockMovementRepositoryDep
from app.modules.patients.dependencies import PatientRepositoryDep
from app.modules.prescriptions.dependencies import PrescriptionServiceDep

def get_sales_repository(session: SessionDep) -> SalesRepository:
    return SalesRepository(session)

SalesRepositoryDep = Annotated[SalesRepository, Depends(get_sales_repository)]

def get_sale_service(
    repo: SalesRepositoryDep,
    medicine_repo: MedicineRepositoryDep,
    batch_repo: MedicineBatchRepositoryDep,
    movement_repo: StockMovementRepositoryDep,
    patient_repo: PatientRepositoryDep,
    prescription_service: PrescriptionServiceDep,
) -> SaleService:
    return SaleService(repo, medicine_repo, batch_repo, movement_repo, patient_repo, prescription_service)

SaleServiceDep = Annotated[SaleService, Depends(get_sale_service)]