import uuid
from datetime import date
from fastapi import APIRouter, status
from app.modules.sales.models import PaymentStatus
from app.modules.sales.schemas import (
    DailyTotalRead, MySaleRead, SaleCreate, SalePaymentUpdate, SaleRead,
)
from app.modules.sales.dependencies import SaleServiceDep
from app.modules.users.dependencies import CurrentUserDep, StaffDep, PharmacyDep
from app.modules.users.models import Role
from app.core.exceptions.errors import ForbiddenError

sale_router = APIRouter(prefix="/sales", tags=["sales"])

@sale_router.post("/add", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
async def add_sale(data: SaleCreate, service: SaleServiceDep, pharmacy: PharmacyDep) -> SaleRead:
    return await service.create_sale(data, sold_by=pharmacy.id)

@sale_router.get("", response_model=list[SaleRead], status_code=status.HTTP_200_OK)
async def list_sales(
    service: SaleServiceDep,
    staff: StaffDep,
    q: str | None = None,
    patient_id: uuid.UUID | None = None,
    sold_by: uuid.UUID | None = None,
    payment_status: PaymentStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[SaleRead]:
    sales, _total = await service.search_sales(q, patient_id, sold_by, payment_status, date_from, date_to, page, page_size)
    return sales

@sale_router.get("/daily-totals", response_model=list[DailyTotalRead], status_code=status.HTTP_200_OK)
async def daily_totals(
    service: SaleServiceDep,
    staff: StaffDep,
    date_from: date,
    date_to: date,
) -> list[DailyTotalRead]:
    return await service.daily_totals(date_from, date_to)

@sale_router.get("/me", response_model=list[MySaleRead], status_code=status.HTTP_200_OK)
async def my_sales(
    service: SaleServiceDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
) -> list[MySaleRead]:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own sales")
    return await service.list_my_sales(user.patient_id, page, page_size)

@sale_router.get("/me/{sale_id}", response_model=MySaleRead, status_code=status.HTTP_200_OK)
async def my_sale(sale_id: uuid.UUID, service: SaleServiceDep, user: CurrentUserDep) -> MySaleRead:
    if user.role != Role.PATIENT or user.patient_id is None:
        raise ForbiddenError("Only patient accounts can view their own sales")
    return await service.get_my_sale_by_id(sale_id, user.patient_id)

@sale_router.get("/sale-no/{sale_no}", response_model=SaleRead, status_code=status.HTTP_200_OK)
async def get_sale_by_sale_no(sale_no: str, service: SaleServiceDep, staff: StaffDep) -> SaleRead:
    return await service.get_sale_by_sale_no(sale_no)

@sale_router.get("/{sale_id}", response_model=SaleRead, status_code=status.HTTP_200_OK)
async def get_sale(sale_id: uuid.UUID, service: SaleServiceDep, staff: StaffDep) -> SaleRead:
    return await service.get_sale_by_id(sale_id)

@sale_router.patch("/{sale_id}/payment", response_model=SaleRead, status_code=status.HTTP_200_OK)
async def update_sale_payment(sale_id: uuid.UUID, data: SalePaymentUpdate, service: SaleServiceDep, pharmacy: PharmacyDep) -> SaleRead:
    return await service.update_payment(sale_id, data)