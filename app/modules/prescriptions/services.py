import uuid
from datetime import date
from app.modules.prescriptions.models import (
    Prescription, PrescriptionItem, PrescriptionStatus, DispenseStatus,
)
from app.modules.prescriptions.schemas import (
    PrescriptionCreate, PrescriptionItemMatch, PrescriptionItemRead,
    PrescriptionRead, MyPrescriptionRead,
)
from app.modules.prescriptions.repositories import PrescriptionRepository
from app.modules.patients.repositories import PatientRepository
from app.modules.medicines.repositories import MedicineRepository
from app.core.exceptions.errors import ForbiddenError, NotFoundError


def _derive_item_status(delivered: int, prescribed: int) -> DispenseStatus:
    if delivered == 0:
        return DispenseStatus.PENDING
    if delivered < prescribed:
        return DispenseStatus.PARTIALLY_DISPENSED
    return DispenseStatus.DISPENSED


class PrescriptionService:
    def __init__(
        self,
        repo: PrescriptionRepository,
        patient_repo: PatientRepository,
        medicine_repo: MedicineRepository,
    ) -> None:
        self.repo = repo
        self.patient_repo = patient_repo
        self.medicine_repo = medicine_repo

    async def _recompute_status(self, prescription: Prescription) -> None:
        if prescription.status == PrescriptionStatus.CANCELLED:
            return
        items = prescription.items
        if items and all(item.dispense_status == DispenseStatus.DISPENSED for item in items):
            prescription.status = PrescriptionStatus.DISPENSED
        elif any(item.dispense_status in (DispenseStatus.PARTIALLY_DISPENSED, DispenseStatus.DISPENSED) for item in items):
            prescription.status = PrescriptionStatus.PARTIALLY_DISPENSED
        else:
            prescription.status = PrescriptionStatus.PENDING

    async def create_prescription(self, data: PrescriptionCreate, recorded_by: uuid.UUID) -> PrescriptionRead:
        if await self.patient_repo.get_by_id(data.patient_id) is None:
            raise NotFoundError("Patient", str(data.patient_id))

        prescription = Prescription(
            patient_id=data.patient_id,
            prescriber_name=data.prescriber_name,
            recorded_by=recorded_by,
            prescription_date=data.prescription_date,
            notes=data.notes,
            items=[
                PrescriptionItem(
                    medicine_name=item.medicine_name,
                    strength=item.strength,
                    instructions=item.instructions,
                    quantity_prescribed=item.quantity_prescribed,
                )
                for item in data.items
            ],
        )

        return PrescriptionRead.model_validate(await self.repo.add(prescription))

    async def get_prescription_by_id(self, prescription_id: uuid.UUID) -> PrescriptionRead:
        prescription = await self.repo.get_by_id(prescription_id)
        if prescription is None:
            raise NotFoundError("Prescription", str(prescription_id))

        return PrescriptionRead.model_validate(prescription)

    async def search_prescriptions(self, q: str | None, patient_id: uuid.UUID | None, status: PrescriptionStatus | None, date_from: date | None, date_to: date | None, page: int, page_size: int) -> tuple[list[PrescriptionRead], int]:
        prescriptions, total = await self.repo.search(q, patient_id, status, date_from, date_to, page, page_size)
        return [PrescriptionRead.model_validate(p) for p in prescriptions], total

    async def list_my_prescriptions(self, patient_id: uuid.UUID, page: int, page_size: int) -> list[MyPrescriptionRead]:
        prescriptions, _total = await self.repo.search(None, patient_id, None, None, None, page, page_size)
        return [MyPrescriptionRead.model_validate(p) for p in prescriptions]

    async def get_my_prescription_by_id(self, prescription_id: uuid.UUID, patient_id: uuid.UUID) -> MyPrescriptionRead:
        prescription = await self.repo.get_for_patient(prescription_id, patient_id)
        if prescription is None:
            raise NotFoundError("Prescription", str(prescription_id))

        return MyPrescriptionRead.model_validate(prescription)

    async def match_item(self, item_id: uuid.UUID, data: PrescriptionItemMatch) -> PrescriptionItemRead:
        item = await self.repo.get_item_by_id(item_id)
        if item is None:
            raise NotFoundError("PrescriptionItem", str(item_id))
        if item.quantity_delivered > 0:
            raise ForbiddenError("Cannot change the medicine of an item that has already been dispensed")
        medicine = await self.medicine_repo.get_by_id(data.medicine_id)
        if medicine is None:
            raise NotFoundError("Medicine", str(data.medicine_id))
        if not medicine.is_active:
            raise ForbiddenError("Medicine is not active")

        item.medicine_id = data.medicine_id

        return PrescriptionItemRead.model_validate(await self.repo.save_item(item))

    async def mark_item_not_available(self, item_id: uuid.UUID) -> PrescriptionItemRead:
        item = await self.repo.get_item_by_id(item_id)
        if item is None:
            raise NotFoundError("PrescriptionItem", str(item_id))
        if item.quantity_delivered > 0:
            raise ForbiddenError("Cannot mark an item not available after part of it was dispensed")

        item.dispense_status = DispenseStatus.NOT_AVAILABLE

        return PrescriptionItemRead.model_validate(await self.repo.save_item(item))

    async def record_item_delivery(self, item_id: uuid.UUID, quantity: int) -> PrescriptionItemRead:
        item = await self.repo.get_item_by_id(item_id)
        if item is None:
            raise NotFoundError("PrescriptionItem", str(item_id))
        if quantity <= 0:
            raise ForbiddenError("Delivered quantity must be more than zero")
        if item.dispense_status == DispenseStatus.NOT_AVAILABLE:
            raise ForbiddenError("This item was marked not available")
        if item.quantity_delivered + quantity > item.quantity_prescribed:
            raise ForbiddenError("Delivered quantity exceeds the prescribed quantity")

        item.quantity_delivered += quantity
        item.dispense_status = _derive_item_status(item.quantity_delivered, item.quantity_prescribed)

        prescription = await self.repo.get_by_id(item.prescription_id)
        if prescription is not None:
            await self._recompute_status(prescription)

        return PrescriptionItemRead.model_validate(await self.repo.save_item(item))

    async def cancel_prescription(self, prescription_id: uuid.UUID) -> PrescriptionRead:
        prescription = await self.repo.get_for_update(prescription_id)
        if prescription is None:
            raise NotFoundError("Prescription", str(prescription_id))
        if prescription.status == PrescriptionStatus.DISPENSED:
            raise ForbiddenError("A fully dispensed prescription cannot be cancelled")

        prescription.status = PrescriptionStatus.CANCELLED

        return PrescriptionRead.model_validate(await self.repo.save(prescription))