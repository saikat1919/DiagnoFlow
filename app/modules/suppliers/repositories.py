import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.modules.suppliers.models import Supplier


class SupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, supplier: Supplier) -> Supplier:
        self.db_session.add(supplier)
        return await self.save(supplier)

    async def save(self, supplier: Supplier) -> Supplier:
        await self.db_session.flush()
        await self.db_session.refresh(supplier)
        return supplier

    async def get_by_id(self, supplier_id: uuid.UUID) -> Supplier | None:
        return await self.db_session.get(Supplier, supplier_id)

    async def get_by_phone(self, phone: str) -> Supplier | None:
        stmt = select(Supplier).where(Supplier.phone == phone)
        return await self.db_session.scalar(stmt)

    async def get_by_email(self, email: str) -> Supplier | None:
        stmt = select(Supplier).where(Supplier.email == email)
        return await self.db_session.scalar(stmt)

    async def search(
            self,
            q: str | None,
            active_only: bool,
            page: int,
            page_size: int
    ) -> tuple[list[Supplier], int]:
        base = select(Supplier)
        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(
                    Supplier.supplier_name.ilike(pattern),
                    Supplier.phone.ilike(pattern),
                    Supplier.email.ilike(pattern),
                )
            )
        if active_only:
            base = base.where(Supplier.is_active.is_(True))
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(Supplier.supplier_name, Supplier.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0