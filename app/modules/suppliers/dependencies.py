from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.suppliers.repositories import SupplierRepository
from app.modules.suppliers.services import SupplierService

def get_supplier_repository(session: SessionDep) -> SupplierRepository:
    return SupplierRepository(session)

SupplierRepositoryDep = Annotated[SupplierRepository, Depends(get_supplier_repository)]

def get_supplier_service(repo: SupplierRepositoryDep) -> SupplierService:
    return SupplierService(repo)

SupplierServiceDep = Annotated[SupplierService, Depends(get_supplier_service)]