import uuid
from decimal import Decimal
from app.modules.diagnostic_test_catalogue.models import Department, TestCatalogue
from app.modules.diagnostic_test_catalogue.schemas import (
    DepartmentCreate, DepartmentRead, DepartmentUpdate,
    TestCreate, TestRead, TestUpdate,
)
from app.modules.diagnostic_test_catalogue.repositories import DepartmentRepository, TestCatalogueRepository
from app.core.exceptions.errors import ConflictError, NotFoundError


class DepartmentService:
    def __init__(self, repo: DepartmentRepository) -> None:
        self.repo = repo

    async def create_department(self, data: DepartmentCreate) -> DepartmentRead:
        if await self.repo.get_by_name(data.name):
            raise ConflictError("Department", data.name)

        department = Department(name=data.name)

        return DepartmentRead.model_validate(await self.repo.add(department))

    async def get_department_by_id(self, department_id: uuid.UUID) -> DepartmentRead:
        department = await self.repo.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department", str(department_id))

        return DepartmentRead.model_validate(department)

    async def list_departments(self, active_only: bool) -> list[DepartmentRead]:
        departments = await self.repo.list_all(active_only)
        return [DepartmentRead.model_validate(d) for d in departments]

    async def update_department(self, department_id: uuid.UUID, data: DepartmentUpdate) -> DepartmentRead:
        department = await self.repo.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department", str(department_id))

        updated_data = data.model_dump(exclude_unset=True)
        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        if "name" in new_data:
            existing = await self.repo.get_by_name(new_data["name"])
            if existing is not None and existing.id != department.id:
                raise ConflictError("Department", new_data["name"])

        for key, value in new_data.items():
            setattr(department, key, value)

        return DepartmentRead.model_validate(await self.repo.save(department))


class TestCatalogueService:
    def __init__(self, repo: TestCatalogueRepository, department_repo: DepartmentRepository) -> None:
        self.repo = repo
        self.department_repo = department_repo

    async def create_test(self, data: TestCreate) -> TestRead:
        if await self.repo.get_by_code(data.test_code):
            raise ConflictError("Test", data.test_code)
        if await self.department_repo.get_by_id(data.department_id) is None:
            raise NotFoundError("Department", str(data.department_id))

        test = TestCatalogue(
            test_code=data.test_code,
            test_name=data.test_name,
            department_id=data.department_id,
            price=data.price,
            expected_delivery_time=data.expected_delivery_time,
        )

        return TestRead.model_validate(await self.repo.add(test))

    async def get_test_by_code(self, test_code: str) -> TestRead:
        test = await self.repo.get_by_code(test_code.upper())
        if test is None:
            raise NotFoundError("Test", test_code)

        return TestRead.model_validate(test)

    async def search_tests(self, q: str | None, department_id: uuid.UUID | None, active_only: bool, page: int, page_size: int) -> tuple[list[TestRead], int]:
        tests, total = await self.repo.search(q, department_id, active_only, page, page_size)
        return [TestRead.model_validate(t) for t in tests], total

    async def update_test(self, test_code: str, data: TestUpdate) -> TestRead:
        test = await self.repo.get_by_code(test_code.upper())
        if test is None:
            raise NotFoundError("Test", test_code)

        updated_data = data.model_dump(exclude_unset=True)
        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        if "department_id" in new_data:
            if await self.department_repo.get_by_id(new_data["department_id"]) is None:
                raise NotFoundError("Department", str(new_data["department_id"]))

        for key, value in new_data.items():
            setattr(test, key, value)

        return TestRead.model_validate(await self.repo.save(test))