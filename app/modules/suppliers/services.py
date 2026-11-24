import uuid
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierRead, SupplierUpdate
from app.modules.suppliers.repositories import SupplierRepository
from app.core.exceptions.errors import ConflictError, NotFoundError


class SupplierService:
    def __init__(self, repo: SupplierRepository) -> None:
        self.repo = repo

    async def create_supplier(self, data: SupplierCreate) -> SupplierRead:
        if await self.repo.get_by_phone(data.phone):
            raise ConflictError("Supplier", data.phone)
        if data.email and await self.repo.get_by_email(data.email):
            raise ConflictError("Supplier", data.email)

        supplier = Supplier(
            supplier_name=data.supplier_name,
            phone=data.phone,
            email=data.email,
        )

        return SupplierRead.model_validate(await self.repo.add(supplier))

    async def get_supplier_by_id(self, supplier_id: uuid.UUID) -> SupplierRead:
        supplier = await self.repo.get_by_id(supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier", str(supplier_id))

        return SupplierRead.model_validate(supplier)

    async def search_suppliers(self, q: str | None, active_only: bool, page: int, page_size: int) -> tuple[list[SupplierRead], int]:
        suppliers, total = await self.repo.search(q, active_only, page, page_size)
        return [SupplierRead.model_validate(s) for s in suppliers], total

    async def update_supplier(self, supplier_id: uuid.UUID, data: SupplierUpdate) -> SupplierRead:
        supplier = await self.repo.get_by_id(supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier", str(supplier_id))

        updated_data = data.model_dump(exclude_unset=True)
        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        if "phone" in new_data:
            existing = await self.repo.get_by_phone(new_data["phone"])
            if existing is not None and existing.id != supplier.id:
                raise ConflictError("Supplier", new_data["phone"])

        if "email" in new_data:
            existing = await self.repo.get_by_email(new_data["email"])
            if existing is not None and existing.id != supplier.id:
                raise ConflictError("Supplier", new_data["email"])

        for key, value in new_data.items():
            setattr(supplier, key, value)

        return SupplierRead.model_validate(await self.repo.save(supplier))