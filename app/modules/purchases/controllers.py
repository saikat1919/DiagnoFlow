import uuid
from datetime import date
from fastapi import APIRouter, status
from app.modules.purchases.models import PaymentStatus
from app.modules.purchases.models import STATUS as PurchaseOrderStatus
from app.modules.purchases.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchasePaymentUpdate,
    ReceiveDelivery
)
from app.modules.purchases.dependencies import PurchaseOrderServiceDep
from app.modules.users.dependencies import StaffDep, PharmacyManagerDep

purchase_router = APIRouter(prefix="/purchases", tags=["purchases"])

@purchase_router.post("/add", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
async def add_order(data: PurchaseOrderCreate, service: PurchaseOrderServiceDep, manager: PharmacyManagerDep) -> PurchaseOrderRead:
    return await service.create_order(data, created_by=manager.id)

@purchase_router.get("", response_model=list[PurchaseOrderRead], status_code=status.HTTP_200_OK)
async def list_orders(
    service: PurchaseOrderServiceDep,
    staff: StaffDep,
    q: str | None = None,
    supplier_id: uuid.UUID | None = None,
    status: PurchaseOrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[PurchaseOrderRead]:
    orders, _total = await service.search_orders(q, supplier_id, status, payment_status, date_from, date_to, page, page_size)
    return orders

@purchase_router.get("/purchase-no/{purchase_no}", response_model=PurchaseOrderRead, status_code=status.HTTP_200_OK)
async def get_order_by_purchase_no(purchase_no: str, service: PurchaseOrderServiceDep, staff: StaffDep) -> PurchaseOrderRead:
    return await service.get_order_by_purchase_no(purchase_no)

@purchase_router.get("/{order_id}", response_model=PurchaseOrderRead, status_code=status.HTTP_200_OK)
async def get_order(order_id: uuid.UUID, service: PurchaseOrderServiceDep, staff: StaffDep) -> PurchaseOrderRead:
    return await service.get_order_by_id(order_id)

@purchase_router.post("/{order_id}/receive", response_model=PurchaseOrderRead, status_code=status.HTTP_200_OK)
async def receive_order(order_id: uuid.UUID, data: ReceiveDelivery, service: PurchaseOrderServiceDep, manager: PharmacyManagerDep) -> PurchaseOrderRead:
    return await service.receive_delivery(order_id, data, received_by=manager.id)

@purchase_router.patch("/{order_id}/cancel", response_model=PurchaseOrderRead, status_code=status.HTTP_200_OK)
async def cancel_order(order_id: uuid.UUID, service: PurchaseOrderServiceDep, manager: PharmacyManagerDep) -> PurchaseOrderRead:
    return await service.cancel_order(order_id)

@purchase_router.patch("/{order_id}/payment", response_model=PurchaseOrderRead, status_code=status.HTTP_200_OK)
async def update_order_payment(order_id: uuid.UUID, data: PurchasePaymentUpdate, service: PurchaseOrderServiceDep, manager: PharmacyManagerDep) -> PurchaseOrderRead:
    return await service.update_payment(order_id, data)