import uuid
from fastapi import APIRouter, status
from app.modules.diagnostic_test_catalogue.schemas import (
    DepartmentCreate, DepartmentRead, DepartmentUpdate,
    TestCreate, TestRead, TestUpdate,
)
from app.modules.diagnostic_test_catalogue.dependencies import DepartmentServiceDep, TestCatalogueServiceDep
from app.modules.users.dependencies import CurrentUserDep, AdminOrLabDep

department_router = APIRouter(prefix="/departments", tags=["departments"])
test_router = APIRouter(prefix="/tests", tags=["tests"])

@department_router.post("/add", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def add_department(data: DepartmentCreate, service: DepartmentServiceDep, admin_or_lab: AdminOrLabDep) -> DepartmentRead:
    return await service.create_department(data)

@department_router.get("", response_model=list[DepartmentRead], status_code=status.HTTP_200_OK)
async def list_departments(
    service: DepartmentServiceDep,
    user: CurrentUserDep,
    active_only: bool = False,
) -> list[DepartmentRead]:
    return await service.list_departments(active_only)

@department_router.get("/{department_id}", response_model=DepartmentRead, status_code=status.HTTP_200_OK)
async def get_department(department_id: uuid.UUID, service: DepartmentServiceDep, user: CurrentUserDep) -> DepartmentRead:
    return await service.get_department_by_id(department_id)

@department_router.patch("/{department_id}", response_model=DepartmentRead, status_code=status.HTTP_200_OK)
async def update_department(department_id: uuid.UUID, data: DepartmentUpdate, service: DepartmentServiceDep, admin_or_lab: AdminOrLabDep) -> DepartmentRead:
    return await service.update_department(department_id, data)

@test_router.post("/add", response_model=TestRead, status_code=status.HTTP_201_CREATED)
async def add_test(data: TestCreate, service: TestCatalogueServiceDep, admin_or_lab: AdminOrLabDep) -> TestRead:
    return await service.create_test(data)

@test_router.get("", response_model=list[TestRead], status_code=status.HTTP_200_OK)
async def list_tests(
    service: TestCatalogueServiceDep,
    user: CurrentUserDep,
    q: str | None = None,
    department_id: uuid.UUID | None = None,
    active_only: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> list[TestRead]:
    tests, _total = await service.search_tests(q, department_id, active_only, page, page_size)
    return tests

@test_router.get("/{test_code}", response_model=TestRead, status_code=status.HTTP_200_OK)
async def get_test(test_code: str, service: TestCatalogueServiceDep, user: CurrentUserDep) -> TestRead:
    return await service.get_test_by_code(test_code)

@test_router.patch("/{test_code}", response_model=TestRead, status_code=status.HTTP_200_OK)
async def update_test(test_code: str, data: TestUpdate, service: TestCatalogueServiceDep, admin_or_lab: AdminOrLabDep) -> TestRead:
    return await service.update_test(test_code, data)