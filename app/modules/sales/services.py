import uuid
from datetime import date
from decimal import Decimal
from app.modules.sales.models import Sale, SaleItem, PaymentStatus
from app.modules.sales.schemas import (
    DailyTotalRead, MySaleRead, SaleCreate, SalePaymentUpdate, SaleRead,
)
from app.modules.sales.repositories import SalesRepository
from app.modules.medicines.repositories import MedicineRepository
from app.modules.inventory.models import MedicineBatchStatus, MovementType, StockMovement
from app.modules.inventory.repositories import MedicineBatchRepository, StockMovementRepository
from app.modules.patients.repositories import PatientRepository
from app.modules.prescriptions.models import PrescriptionStatus
from app.modules.prescriptions.services import PrescriptionService
from app.core.exceptions.errors import ForbiddenError, NotFoundError


class SaleService:
    def __init__(
        self,
        repo: SalesRepository,
        medicine_repo: MedicineRepository,
        batch_repo: MedicineBatchRepository,
        movement_repo: StockMovementRepository,
        patient_repo: PatientRepository,
        prescription_service: PrescriptionService,
    ) -> None:
        self.repo = repo
        self.medicine_repo = medicine_repo
        self.batch_repo = batch_repo
        self.movement_repo = movement_repo
        self.patient_repo = patient_repo
        self.prescription_service = prescription_service

    async def create_sale(self, data: SaleCreate, sold_by: uuid.UUID) -> SaleRead:
        today = date.today()

        if data.patient_id is not None and await self.patient_repo.get_by_id(data.patient_id) is None:
            raise NotFoundError("Patient", str(data.patient_id))

        prescription = None
        if data.prescription_id is not None:
            prescription = await self.prescription_service.get_prescription_by_id(data.prescription_id)
            if prescription.patient.id != data.patient_id:
                raise ForbiddenError("This prescription belongs to another patient")
            if prescription.status == PrescriptionStatus.CANCELLED:
                raise ForbiddenError("Cannot sell against a cancelled prescription")

        grouped: dict[tuple[uuid.UUID, uuid.UUID | None], int] = {}
        for item in data.items:
            key = (item.medicine_id, item.batch_id)
            grouped[key] = grouped.get(key, 0) + item.quantity

        medicines = {}
        for medicine_id, _batch_id in grouped:
            if medicine_id not in medicines:
                medicine = await self.medicine_repo.get_by_id(medicine_id)
                if medicine is None:
                    raise NotFoundError("Medicine", str(medicine_id))
                if not medicine.is_active:
                    raise ForbiddenError(f"Medicine {medicine.brand_name} is not active")
                medicines[medicine_id] = medicine

        plan = []
        for (medicine_id, batch_id), quantity in grouped.items():
            medicine = medicines[medicine_id]
            if batch_id is not None:
                batch = await self.batch_repo.get_for_update(batch_id)
                if batch is None:
                    raise NotFoundError("MedicineBatch", str(batch_id))
                if batch.medicine_id != medicine_id:
                    raise ForbiddenError("Batch does not belong to this medicine")
                if batch.status != MedicineBatchStatus.ACTIVE:
                    raise ForbiddenError("Batch is not active")
                if batch.expiry_date < today:
                    raise ForbiddenError("Batch is expired")
                if batch.quantity_in_stock < quantity:
                    raise ForbiddenError("Not enough stock in this batch")
                allocations = [(batch, quantity)]
            else:
                batches = await self.batch_repo.get_usable_for_update(medicine_id, today)
                if sum(b.quantity_in_stock for b in batches) < quantity:
                    raise ForbiddenError(f"Not enough stock for {medicine.brand_name}")
                allocations = []
                remaining = quantity
                for batch in batches:
                    take = min(batch.quantity_in_stock, remaining)
                    allocations.append((batch, take))
                    remaining -= take
                    if remaining == 0:
                        break
            plan.append((medicine, allocations))

        delivery_plan: list[tuple[uuid.UUID, int]] = []
        if prescription is not None:
            requested_per_medicine: dict[uuid.UUID, int] = {}
            for (medicine_id, _batch_id), quantity in grouped.items():
                requested_per_medicine[medicine_id] = requested_per_medicine.get(medicine_id, 0) + quantity
            for medicine_id, quantity in requested_per_medicine.items():
                remaining_items = [
                    item for item in prescription.items
                    if item.medicine is not None
                    and item.medicine.id == medicine_id
                    and item.dispense_status != "not_available"
                    and item.quantity_prescribed - item.quantity_delivered > 0
                ]
                if not remaining_items:
                    raise ForbiddenError("This medicine is not on the prescription or is not available")
                left = quantity
                for item in remaining_items:
                    take = min(item.quantity_prescribed - item.quantity_delivered, left)
                    delivery_plan.append((item.id, take))
                    left -= take
                    if left == 0:
                        break
                if left > 0:
                    raise ForbiddenError("Quantity exceeds what is still undelivered on the prescription")

        sale_items: list[SaleItem] = []
        subtotal = Decimal("0")
        for medicine, allocations in plan:
            for batch, quantity in allocations:
                batch.quantity_in_stock -= quantity
                await self.batch_repo.save(batch)
                await self.movement_repo.add(
                    StockMovement(
                        batch_id=batch.id,
                        movement_type=MovementType.SOLD,
                        quantity=-quantity,
                        created_by=sold_by,
                    )
                )
                line_total = Decimal(quantity) * medicine.selling_price
                subtotal += line_total
                sale_items.append(
                    SaleItem(
                        batch_id=batch.id,
                        quantity=quantity,
                        unit_price=medicine.selling_price,
                        line_total=line_total,
                    )
                )

        if data.discount > subtotal:
            raise ForbiddenError("Discount cannot be more than the subtotal")

        for item_id, quantity in delivery_plan:
            await self.prescription_service.record_item_delivery(item_id, quantity)

        sale = Sale(
            patient_id=data.patient_id,
            prescription_id=data.prescription_id,
            sold_by=sold_by,
            subtotal=subtotal,
            discount=data.discount,
            total_amount=subtotal - data.discount,
            payment_method=data.payment_method,
            payment_status=data.payment_status,
            items=sale_items,
        )

        return SaleRead.model_validate(await self.repo.add(sale))

    async def get_sale_by_id(self, sale_id: uuid.UUID) -> SaleRead:
        sale = await self.repo.get_by_id(sale_id)
        if sale is None:
            raise NotFoundError("Sale", str(sale_id))

        return SaleRead.model_validate(sale)

    async def get_sale_by_sale_no(self, sale_no: str) -> SaleRead:
        sale = await self.repo.get_by_sale_no(sale_no)
        if sale is None:
            raise NotFoundError("Sale", sale_no)

        return SaleRead.model_validate(sale)

    async def search_sales(self, q: str | None, patient_id: uuid.UUID | None, sold_by: uuid.UUID | None, payment_status: PaymentStatus | None, date_from: date | None, date_to: date | None, page: int, page_size: int) -> tuple[list[SaleRead], int]:
        sales, total = await self.repo.search(q, patient_id, sold_by, payment_status, date_from, date_to, page, page_size)
        return [SaleRead.model_validate(s) for s in sales], total

    async def list_my_sales(self, patient_id: uuid.UUID, page: int, page_size: int) -> list[MySaleRead]:
        sales, _total = await self.repo.search(None, patient_id, None, None, None, None, page, page_size)
        return [MySaleRead.model_validate(s) for s in sales]

    async def get_my_sale_by_id(self, sale_id: uuid.UUID, patient_id: uuid.UUID) -> MySaleRead:
        sale = await self.repo.get_for_patient(sale_id, patient_id)
        if sale is None:
            raise NotFoundError("Sale", str(sale_id))

        return MySaleRead.model_validate(sale)

    async def update_payment(self, sale_id: uuid.UUID, data: SalePaymentUpdate) -> SaleRead:
        sale = await self.repo.get_by_id(sale_id)
        if sale is None:
            raise NotFoundError("Sale", str(sale_id))
        if sale.payment_status == PaymentStatus.PAID and data.payment_status == PaymentStatus.PENDING:
            raise ForbiddenError("A paid sale cannot go back to pending")

        sale.payment_status = data.payment_status
        sale.payment_method = data.payment_method

        return SaleRead.model_validate(await self.repo.save(sale))

    async def daily_totals(self, date_from: date, date_to: date) -> list[DailyTotalRead]:
        if date_from > date_to:
            raise ForbiddenError("date_from must be on or before date_to")

        rows = await self.repo.daily_totals(date_from, date_to)
        return [
            DailyTotalRead(
                sale_date=day,
                sale_count=count,
                total_amount=total or Decimal("0"),
                paid_amount=paid or Decimal("0"),
            )
            for day, count, total, paid in rows
        ]