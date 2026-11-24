import uuid
from app.modules.medicines.models import Medicine
from app.modules.medicines.schemas import MedicineCreate, MedicineRead, MedicineUpdate
from app.modules.medicines.repositories import MedicineRepository
from app.core.exceptions.errors import ConflictError, NotFoundError


class MedicineService:
    def __init__(self, repo: MedicineRepository) -> None:
        self.repo = repo

    async def create_medicine(self, data: MedicineCreate) -> MedicineRead:
        if await self.repo.get_by_identity(data.brand_name, data.strength, data.dosage_form):
            raise ConflictError("Medicine", f"{data.brand_name} {data.strength}")

        medicine = Medicine(
            brand_name=data.brand_name,
            generic_name=data.generic_name,
            strength=data.strength,
            dosage_form=data.dosage_form,
            description=data.description,
            selling_price=data.selling_price,
            reorder_level=data.reorder_level,
        )

        return MedicineRead.model_validate(await self.repo.add(medicine))

    async def get_medicine_by_id(self, medicine_id: uuid.UUID) -> MedicineRead:
        medicine = await self.repo.get_by_id(medicine_id)
        if medicine is None:
            raise NotFoundError("Medicine", str(medicine_id))

        return MedicineRead.model_validate(medicine)

    async def search_medicines(self, q: str | None, dosage_form, active_only: bool, page: int, page_size: int) -> tuple[list[MedicineRead], int]:
        medicines, total = await self.repo.search(q, dosage_form, active_only, page, page_size)
        return [MedicineRead.model_validate(m) for m in medicines], total

    async def update_medicine(self, medicine_id: uuid.UUID, data: MedicineUpdate) -> MedicineRead:
        medicine = await self.repo.get_by_id(medicine_id)
        if medicine is None:
            raise NotFoundError("Medicine", str(medicine_id))

        updated_data = data.model_dump(exclude_unset=True)
        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        new_brand = new_data.get("brand_name", medicine.brand_name)
        new_strength = new_data.get("strength", medicine.strength)
        new_form = new_data.get("dosage_form", medicine.dosage_form)
        if (new_brand, new_strength, new_form) != (medicine.brand_name, medicine.strength, medicine.dosage_form):
            existing = await self.repo.get_by_identity(new_brand, new_strength, new_form)
            if existing is not None and existing.id != medicine.id:
                raise ConflictError("Medicine", f"{new_brand} {new_strength}")

        for key, value in new_data.items():
            setattr(medicine, key, value)

        return MedicineRead.model_validate(await self.repo.save(medicine))