import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.diagnostic_test_catalogue.models import Department, TestCatalogue


class DepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, department: Department) -> Department:
        self.db_session.add(department)
        return await self.save(department)

    async def save(self, department: Department) -> Department:
        await self.db_session.flush()
        await self.db_session.refresh(department)
        return department

    async def get_by_id(self, department_id: uuid.UUID) -> Department | None:
        return await self.db_session.get(Department, department_id)

    async def get_by_name(self, name: str) -> Department | None:
        stmt = select(Department).where(func.lower(Department.name) == name.lower())
        return await self.db_session.scalar(stmt)

    async def list_all(self, active_only: bool = False) -> list[Department]:
        stmt = select(Department).order_by(Department.name)
        if active_only:
            stmt = stmt.where(Department.is_active.is_(True))
        return list((await self.db_session.scalars(stmt)).all())


class TestCatalogueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, test: TestCatalogue) -> TestCatalogue:
        self.db_session.add(test)
        return await self.save(test)

    async def save(self, test: TestCatalogue) -> TestCatalogue:
        await self.db_session.flush()
        await self.db_session.refresh(test)
        return test

    async def get_by_code(self, test_code: str) -> TestCatalogue | None:
        return await self.db_session.get(TestCatalogue, test_code)

    async def get_by_codes(self, test_codes: list) -> list[TestCatalogue]:
        stmt = select(TestCatalogue).where(TestCatalogue.test_code.in_(test_codes))
        return list((await self.db_session.scalars(stmt)).all())

    async def search(self, q: str | None,
                     department_id: uuid.UUID | None,
                     active_only: bool,
                     page: int, page_size: int) -> tuple[list[TestCatalogue], int]:
        base = select(TestCatalogue)
        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(
                    TestCatalogue.test_code.ilike(pattern),
                    TestCatalogue.test_name.ilike(pattern)
                )
            )

        if department_id is not None:
            base = base.where(TestCatalogue.department_id == department_id)
        if active_only:
            base = base.where(TestCatalogue.is_active.is_(True))
        total = await self.db_session.scalar(
            select(func.count().select_from(base.subquery()))
        )
        stmt = (
            base.order_by(TestCatalogue.test_name, TestCatalogue.test_code)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0