from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.diagnostic_test_catalogue.repositories import DepartmentRepository, TestCatalogueRepository
from app.modules.diagnostic_test_catalogue.services import DepartmentService, TestCatalogueService

def get_department_repository(session: SessionDep) -> DepartmentRepository:
    return DepartmentRepository(session)

DepartmentRepositoryDep = Annotated[DepartmentRepository, Depends(get_department_repository)]

def get_department_service(repo: DepartmentRepositoryDep) -> DepartmentService:
    return DepartmentService(repo)

DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]

def get_test_catalogue_repository(session: SessionDep) -> TestCatalogueRepository:
    return TestCatalogueRepository(session)

TestCatalogueRepositoryDep = Annotated[TestCatalogueRepository, Depends(get_test_catalogue_repository)]

def get_test_catalogue_service(
    repo: TestCatalogueRepositoryDep,
    department_repo: DepartmentRepositoryDep,
) -> TestCatalogueService:
    return TestCatalogueService(repo, department_repo)

TestCatalogueServiceDep = Annotated[TestCatalogueService, Depends(get_test_catalogue_service)]