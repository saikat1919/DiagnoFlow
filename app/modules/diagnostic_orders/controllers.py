import uuid
from fastapi import APIRouter, status
from app.modules.diagnostic_orders.models import WorkStatus, PaymentStatus
from app.modules.diagnostic_orders.schemas import (
    OrderCreate, OrderItemRead, OrderItemStatusUpdate, OrderPaymentUpdate,
    OrderRead, OrderStatusUpdate, MyOrderRead,
)
from app.modules.diagnostic_orders.dependencies import DiagnosticOrderServiceDep
from app.modules.users.dependencies import CurrentUserDep, StaffDep, AdminDep, AdminOrLabDep, AdminOrReceptionistDep
from app.modules.users.models import Role
from app.core.exceptions.errors import ForbiddenError

diagnostic_order_router = APIRouter(prefix="/diagnostic-orders", tags=["diagnostic orders"])

@diagnostic_order_router.post("/add", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def add_order(data: OrderCreate, service: DiagnosticOrderServiceDep, staff: AdminOrReceptionistDep) -> OrderRead:
    return await service.create_order(data, created_by=staff.id)

@diagnostic_order_router.get("", response_model=list[OrderRead], status_code=status.HTTP_200_OK)
async def list_orders(
    service: DiagnosticOrderServiceDep,
    staff: StaffDep,
    q: str | None = None,
    patient_id: uuid.UUID | None = None,
    status: WorkStatus | None = None,
    payment_status: PaymentStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[OrderRead]:
    orders, _total = await service.search_orders(q, patient_id, status, payment_status, page, page_size)
    return orders

@diagnostic_order_router.get("/me", response_model=list[MyOrderRead], status_code=status.HTTP_200_OK)
async def my_orders(
    service: DiagnosticOrderServiceDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> list[MyOrderRead]:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own orders")
    return await service.list_my_orders(user.patient_id, page, page_size)

@diagnostic_order_router.get("/me/{order_id}", response_model=MyOrderRead, status_code=status.HTTP_200_OK)
async def my_order(order_id: uuid.UUID, service: DiagnosticOrderServiceDep, user: CurrentUserDep) -> MyOrderRead:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own orders")
    return await service.get_my_order_by_id(order_id, user.patient_id)

@diagnostic_order_router.get("/invoice/{invoice_no}", response_model=OrderRead, status_code=status.HTTP_200_OK)
async def get_order_by_invoice(invoice_no: str, service: DiagnosticOrderServiceDep, staff: StaffDep) -> OrderRead:
    return await service.get_order_by_invoice_no(invoice_no)

@diagnostic_order_router.get("/{order_id}", response_model=OrderRead, status_code=status.HTTP_200_OK)
async def get_order(order_id: uuid.UUID, service: DiagnosticOrderServiceDep, staff: StaffDep) -> OrderRead:
    return await service.get_order_by_id(order_id)

@diagnostic_order_router.patch("/{order_id}/status", response_model=OrderRead, status_code=status.HTTP_200_OK)
async def update_order_status(order_id: uuid.UUID, data: OrderStatusUpdate, service: DiagnosticOrderServiceDep, staff: AdminOrLabDep) -> OrderRead:
    return await service.update_order_status(order_id, data)

@diagnostic_order_router.patch("/{order_id}/payment", response_model=OrderRead, status_code=status.HTTP_200_OK)
async def update_order_payment(order_id: uuid.UUID, data: OrderPaymentUpdate, service: DiagnosticOrderServiceDep, staff: AdminOrReceptionistDep) -> OrderRead:
    return await service.update_order_payment(order_id, data)

@diagnostic_order_router.patch("/items/{item_id}/status", response_model=OrderItemRead, status_code=status.HTTP_200_OK)
async def update_order_item_status(item_id: uuid.UUID, data: OrderItemStatusUpdate, service: DiagnosticOrderServiceDep, staff: AdminOrLabDep) -> OrderItemRead:
    return await service.update_order_item_status(item_id, data)