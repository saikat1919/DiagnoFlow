import uuid
from datetime import UTC, datetime
from decimal import Decimal
from app.modules.purchases.models import PurchaseOrder, PurchaseOrderItem, PaymentStatus
from app.modules.purchases.models import STATUS as PurchaseOrderStatus
from app.modules.purchases.schemas import (
    PurchaseOrderCreate, PurchaseOrderRead, PurchasePaymentUpdate, ReceiveDelivery,
)
from app.modules.purchases.repositories import PurchaseOrderRepository
from app.modules.suppliers.repositories import SupplierRepository
from app.modules.medicines.repositories import MedicineRepository
from app.modules.inventory.models import MedicineBatch, StockMovement, MovementType
from app.modules.inventory.repositories import MedicineBatchRepository, StockMovementRepository
from app.core.exceptions.errors import ForbiddenError, NotFoundError


class PurchaseOrderService:
    def __init__(
        self,
        repo: PurchaseOrderRepository,
        supplier_repo: SupplierRepository,
        medicine_repo: MedicineRepository,
        batch_repo: MedicineBatchRepository,
        movement_repo: StockMovementRepository,
    ) -> None:
        self.repo = repo
        self.supplier_repo = supplier_repo
        self.medicine_repo = medicine_repo
        self.batch_repo = batch_repo
        self.movement_repo = movement_repo

    async def create_order(self, data: PurchaseOrderCreate, created_by: uuid.UUID) -> PurchaseOrderRead:
        supplier = await self.supplier_repo.get_by_id(data.supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier", str(data.supplier_id))
        if not supplier.is_active:
            raise ForbiddenError("Supplier is not active")

        medicines = await self.medicine_repo.get_by_ids([item.medicine_id for item in data.items])
        found = {medicine.id: medicine for medicine in medicines}
        for item in data.items:
            medicine = found.get(item.medicine_id)
            if medicine is None:
                raise NotFoundError("Medicine", str(item.medicine_id))
            if not medicine.is_active:
                raise ForbiddenError(f"Medicine {medicine.brand_name} is not active")

        total = sum(
            (Decimal(item.quantity_ordered) * item.unit_cost for item in data.items),
            Decimal("0"),
        )
        order = PurchaseOrder(
            supplier_id=data.supplier_id,
            created_by=created_by,
            expected_delivery=data.expected_delivery,
            total_amount=total,
            items=[
                PurchaseOrderItem(
                    medicine_id=item.medicine_id,
                    quantity_ordered=item.quantity_ordered,
                    unit_cost=item.unit_cost,
                )
                for item in data.items
            ],
        )

        return PurchaseOrderRead.model_validate(await self.repo.add(order))

    async def get_order_by_id(self, order_id: uuid.UUID) -> PurchaseOrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("PurchaseOrder", str(order_id))

        return PurchaseOrderRead.model_validate(order)

    async def get_order_by_purchase_no(self, purchase_no: str) -> PurchaseOrderRead:
        order = await self.repo.get_by_purchase_no(purchase_no)
        if order is None:
            raise NotFoundError("PurchaseOrder", purchase_no)

        return PurchaseOrderRead.model_validate(order)

    async def search_orders(self, q: str | None, supplier_id: uuid.UUID | None, status: PurchaseOrderStatus | None, payment_status: PaymentStatus | None, date_from, date_to, page: int, page_size: int) -> tuple[list[PurchaseOrderRead], int]:
        orders, total = await self.repo.search(q, supplier_id, status, payment_status, date_from, date_to, page, page_size)
        return [PurchaseOrderRead.model_validate(o) for o in orders], total

    async def receive_delivery(self, order_id: uuid.UUID, data: ReceiveDelivery, received_by: uuid.UUID) -> PurchaseOrderRead:
        order = await self.repo.get_for_update(order_id)
        if order is None:
            raise NotFoundError("PurchaseOrder", str(order_id))
        if order.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
            raise ForbiddenError(f"Cannot receive a {order.status.value} order")

        items_by_id = {item.id: item for item in order.items}
        requested: dict[uuid.UUID, int] = {}
        for receive_item in data.items:
            requested[receive_item.purchase_order_item_id] = (
                requested.get(receive_item.purchase_order_item_id, 0) + receive_item.quantity_received
            )
        for item_id, quantity in requested.items():
            item = items_by_id.get(item_id)
            if item is None:
                raise NotFoundError("PurchaseOrderItem", str(item_id))
            if item.quantity_received + quantity > item.quantity_ordered:
                raise ForbiddenError(
                    f"Receiving {quantity} more of {item.medicine_id} exceeds the ordered quantity"
                )

        for receive_item in data.items:
            item = items_by_id[receive_item.purchase_order_item_id]
            batch = await self.batch_repo.get_by_identity(
                item.medicine_id, order.supplier_id, receive_item.batch_no
            )
            if batch is None:
                batch = MedicineBatch(
                    medicine_id=item.medicine_id,
                    supplier_id=order.supplier_id,
                    batch_no=receive_item.batch_no,
                    expiry_date=receive_item.expiry_date,
                    quantity_received=receive_item.quantity_received,
                    quantity_in_stock=receive_item.quantity_received,
                    purchase_price=item.unit_cost,
                )
                batch = await self.batch_repo.add(batch)
            else:
                batch.quantity_received += receive_item.quantity_received
                batch.quantity_in_stock += receive_item.quantity_received
                batch = await self.batch_repo.save(batch)

            item.quantity_received += receive_item.quantity_received
            await self.movement_repo.add(
                StockMovement(
                    batch_id=batch.id,
                    movement_type=MovementType.RECEIVED,
                    quantity=receive_item.quantity_received,
                    created_by=received_by,
                )
            )

        if all(item.quantity_received == item.quantity_ordered for item in order.items):
            order.status = PurchaseOrderStatus.RECEIVED
            order.delivered_at = datetime.now(UTC)
        else:
            order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

        return PurchaseOrderRead.model_validate(await self.repo.save(order))

    async def cancel_order(self, order_id: uuid.UUID) -> PurchaseOrderRead:
        order = await self.repo.get_for_update(order_id)
        if order is None:
            raise NotFoundError("PurchaseOrder", str(order_id))
        if order.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
            raise ForbiddenError(f"Cannot cancel a {order.status.value} order")

        order.status = PurchaseOrderStatus.CANCELLED

        return PurchaseOrderRead.model_validate(await self.repo.save(order))

    async def update_payment(self, order_id: uuid.UUID, data: PurchasePaymentUpdate) -> PurchaseOrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("PurchaseOrder", str(order_id))
        if order.payment_status == PaymentStatus.PAID and data.payment_status != PaymentStatus.PAID:
            raise ForbiddenError("A paid order cannot go back to unpaid")

        order.payment_status = data.payment_status

        return PurchaseOrderRead.model_validate(await self.repo.save(order))