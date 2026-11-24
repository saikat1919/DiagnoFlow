import uuid
from decimal import Decimal
from app.modules.diagnostic_orders.models import DiagnosticOrder, DiagnosticOrderItem, WorkStatus
from app.modules.diagnostic_orders.schemas import (
    OrderCreate, OrderItemRead, OrderItemStatusUpdate, OrderPaymentUpdate,
    OrderRead, OrderStatusUpdate, MyOrderRead, MyOrderItemRead,
)
from app.modules.diagnostic_orders.models import PaymentStatus
from app.modules.diagnostic_orders.repositories import DiagnosticOrderRepository
from app.modules.patients.repositories import PatientRepository
from app.modules.diagnostic_test_catalogue.repositories import TestCatalogueRepository
from app.core.exceptions.errors import ConflictError, ForbiddenError, NotFoundError

_ALLOWED_TRANSITIONS = {
    WorkStatus.REGISTERED: {WorkStatus.SAMPLE_COLLECTED, WorkStatus.CANCELLED},
    WorkStatus.SAMPLE_COLLECTED: {WorkStatus.PROCESSING, WorkStatus.CANCELLED},
    WorkStatus.PROCESSING: {WorkStatus.COMPLETED, WorkStatus.CANCELLED},
    WorkStatus.COMPLETED: set(),
    WorkStatus.CANCELLED: set(),
}


def _check_transition(current: WorkStatus, new: WorkStatus, what: str) -> None:
    if new != current and new not in _ALLOWED_TRANSITIONS[current]:
        raise ForbiddenError(f"Cannot move {what} from {current.value} to {new.value}")


class DiagnosticOrderService:
    def __init__(
        self,
        repo: DiagnosticOrderRepository,
        patient_repo: PatientRepository,
        test_repo: TestCatalogueRepository,
    ) -> None:
        self.repo = repo
        self.patient_repo = patient_repo
        self.test_repo = test_repo

    async def create_order(self, data: OrderCreate, created_by: uuid.UUID) -> OrderRead:
        if await self.patient_repo.get_by_id(data.patient_id) is None:
            raise NotFoundError("Patient", str(data.patient_id))

        codes = [item.test_code for item in data.items]
        tests = await self.test_repo.get_by_codes(codes)
        found = {test.test_code: test for test in tests}
        missing = [code for code in codes if code not in found]
        if missing:
            raise NotFoundError("Test", missing[0])
        inactive = [code for code in codes if not found[code].is_active]
        if inactive:
            raise ForbiddenError(f"Test {inactive[0]} is not active")

        total = sum((found[code].price for code in codes), Decimal("0"))
        order = DiagnosticOrder(
            patient_id=data.patient_id,
            created_by=created_by,
            expected_delivery=data.expected_delivery,
            total_amount=total,
            items=[
                DiagnosticOrderItem(test_code=code, price_at_order=found[code].price)
                for code in codes
            ],
        )

        return OrderRead.model_validate(await self.repo.add(order))

    async def get_order_by_id(self, order_id: uuid.UUID) -> OrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("DiagnosticOrder", str(order_id))

        return OrderRead.model_validate(order)

    async def get_order_by_invoice_no(self, invoice_no: str) -> OrderRead:
        order = await self.repo.get_by_invoice_no(invoice_no)
        if order is None:
            raise NotFoundError("DiagnosticOrder", invoice_no)

        return OrderRead.model_validate(order)

    async def search_orders(self, q: str | None, patient_id: uuid.UUID | None, status: WorkStatus | None, payment_status: PaymentStatus | None, page: int, page_size: int) -> tuple[list[OrderRead], int]:
        orders, total = await self.repo.search(q, patient_id, status, payment_status, page, page_size)
        return [OrderRead.model_validate(o) for o in orders], total

    async def list_my_orders(self, patient_id: uuid.UUID, page: int, page_size: int) -> list[MyOrderRead]:
        orders, _total = await self.repo.search(None, patient_id, None, None, page, page_size)
        return [MyOrderRead.model_validate(o) for o in orders]

    async def get_my_order_by_id(self, order_id: uuid.UUID, patient_id: uuid.UUID) -> MyOrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("DiagnosticOrder", str(order_id))
        if order.patient_id != patient_id:
            raise ForbiddenError("This order belongs to another patient")

        return MyOrderRead.model_validate(order)

    async def update_order_status(self, order_id: uuid.UUID, data: OrderStatusUpdate) -> OrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("DiagnosticOrder", str(order_id))

        _check_transition(order.status, data.status, "order")
        order.status = data.status
        if data.status == WorkStatus.CANCELLED:
            for item in order.items:
                if item.item_status != WorkStatus.COMPLETED:
                    item.item_status = WorkStatus.CANCELLED

        return OrderRead.model_validate(await self.repo.save(order))

    async def update_order_item_status(self, item_id: uuid.UUID, data: OrderItemStatusUpdate) -> OrderItemRead:
        item = await self.repo.get_item_by_id(item_id)
        if item is None:
            raise NotFoundError("DiagnosticOrderItem", str(item_id))

        _check_transition(item.item_status, data.item_status, "order item")
        item.item_status = data.item_status

        return OrderItemRead.model_validate(await self.repo.save_item(item))

    async def update_order_payment(self, order_id: uuid.UUID, data: OrderPaymentUpdate) -> OrderRead:
        order = await self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("DiagnosticOrder", str(order_id))
        if order.payment_status == PaymentStatus.PAID and data.payment_status == PaymentStatus.PENDING:
            raise ForbiddenError("A paid order cannot go back to pending")

        order.payment_status = data.payment_status

        return OrderRead.model_validate(await self.repo.save(order))