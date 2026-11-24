from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.diagnostic_orders.repositories import DiagnosticOrderRepository
from app.modules.diagnostic_orders.services import DiagnosticOrderService
from app.modules.patients.dependencies import PatientRepositoryDep
from app.modules.diagnostic_test_catalogue.dependencies import TestCatalogueRepositoryDep

def get_order_repository(session: SessionDep) -> DiagnosticOrderRepository:
    return DiagnosticOrderRepository(session)

DiagnosticOrderRepositoryDep = Annotated[DiagnosticOrderRepository, Depends(get_order_repository)]

def get_order_service(
    repo: DiagnosticOrderRepositoryDep,
    patient_repo: PatientRepositoryDep,
    test_repo: TestCatalogueRepositoryDep,
) -> DiagnosticOrderService:
    return DiagnosticOrderService(repo, patient_repo, test_repo)

DiagnosticOrderServiceDep = Annotated[DiagnosticOrderService, Depends(get_order_service)]