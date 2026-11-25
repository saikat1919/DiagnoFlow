import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.diagnostic_orders.models import DiagnosticOrder, DiagnosticOrderItem, WorkStatus
from app.modules.diagnostic_test_catalogue.models import TestCatalogue
from app.modules.inventory.models import MedicineBatch, MedicineBatchStatus
from app.modules.medicines.models import Medicine
from app.modules.patients.models import Patient
from app.modules.prescriptions.models import DispenseStatus, Prescription, PrescriptionItem, PrescriptionStatus
from app.modules.purchases.models import PurchaseOrder
from app.modules.sales.models import Sale
from app.modules.sales.models import PaymentStatus as SalePaymentStatus
from app.modules.test_reports.models import DiagnosticTestReport, ReportStatus
from app.modules.users.models import User


def _money(value: Decimal | None) -> str:
    return str(value or Decimal("0"))


def _counts(rows) -> dict[str, int]:
    return {status.value: int(count) for status, count in rows}


class SummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def patient_summary(self, day: date) -> dict:
        registered = await self.db_session.scalar(
            select(func.count(Patient.id)).where(cast(Patient.created_at, Date) == day)
        )
        total = await self.db_session.scalar(select(func.count(Patient.id)))
        return {"date": day.isoformat(), "registered_today": int(registered or 0), "total_patients": int(total or 0)}

    async def user_summary(self) -> dict:
        rows = await self.db_session.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        active = await self.db_session.scalar(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
        return {"by_role": _counts(rows.all()), "active_users": int(active or 0)}

    async def order_summary(self, day: date) -> dict:
        by_status = await self.db_session.execute(
            select(DiagnosticOrder.status, func.count(DiagnosticOrder.id))
            .where(cast(DiagnosticOrder.order_date, Date) == day)
            .group_by(DiagnosticOrder.status)
        )
        by_payment = await self.db_session.execute(
            select(DiagnosticOrder.payment_status, func.count(DiagnosticOrder.id))
            .where(cast(DiagnosticOrder.order_date, Date) == day)
            .group_by(DiagnosticOrder.payment_status)
        )
        total_amount = await self.db_session.scalar(
            select(func.coalesce(func.sum(DiagnosticOrder.total_amount), 0)).where(
                cast(DiagnosticOrder.order_date, Date) == day
            )
        )
        return {
            "date": day.isoformat(),
            "by_status": _counts(by_status.all()),
            "by_payment_status": _counts(by_payment.all()),
            "total_amount": _money(total_amount),
        }

    async def report_summary(self, day: date) -> dict:
        by_status = await self.db_session.execute(
            select(DiagnosticTestReport.report_status, func.count(DiagnosticTestReport.id))
            .group_by(DiagnosticTestReport.report_status)
        )
        released_today = await self.db_session.scalar(
            select(func.count(DiagnosticTestReport.id)).where(
                cast(DiagnosticTestReport.released_at, Date) == day
            )
        )
        return {
            "date": day.isoformat(),
            "by_status": _counts(by_status.all()),
            "released_today": int(released_today or 0),
        }

    async def sales_summary(self, day: date) -> dict:
        rows = await self.db_session.execute(
            select(
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(
                    func.sum(Sale.total_amount).filter(Sale.payment_status == SalePaymentStatus.PAID), 0
                ),
            ).where(cast(Sale.sale_date, Date) == day)
        )
        count, total, paid = rows.one()
        by_payment = await self.db_session.execute(
            select(Sale.payment_status, func.count(Sale.id))
            .where(cast(Sale.sale_date, Date) == day)
            .group_by(Sale.payment_status)
        )
        return {
            "date": day.isoformat(),
            "sale_count": int(count),
            "total_amount": _money(total),
            "paid_amount": _money(paid),
            "by_payment_status": _counts(by_payment.all()),
        }

    async def pharmacy_summary(self, today: date, expiring_days: int = 30) -> dict:
        usable = (
            select(
                MedicineBatch.medicine_id,
                func.coalesce(func.sum(MedicineBatch.quantity_in_stock), 0).label("stock"),
            )
            .where(
                MedicineBatch.status == MedicineBatchStatus.ACTIVE,
                MedicineBatch.expiry_date >= today,
                MedicineBatch.quantity_in_stock > 0,
            )
            .group_by(MedicineBatch.medicine_id)
            .subquery()
        )
        low_rows = await self.db_session.execute(
            select(
                Medicine.brand_name,
                Medicine.generic_name,
                Medicine.strength,
                func.coalesce(usable.c.stock, 0),
            )
            .outerjoin(usable, usable.c.medicine_id == Medicine.id)
            .where(
                Medicine.is_active.is_(True),
                func.coalesce(usable.c.stock, 0) < Medicine.reorder_level,
            )
            .order_by(Medicine.brand_name)
        )
        expiring_rows = await self.db_session.execute(
            select(
                Medicine.brand_name,
                Medicine.strength,
                MedicineBatch.batch_no,
                MedicineBatch.expiry_date,
                MedicineBatch.quantity_in_stock,
            )
            .join(Medicine, Medicine.id == MedicineBatch.medicine_id)
            .where(
                MedicineBatch.status == MedicineBatchStatus.ACTIVE,
                MedicineBatch.expiry_date >= today,
                MedicineBatch.expiry_date <= today + timedelta(days=expiring_days),
                MedicineBatch.quantity_in_stock > 0,
            )
            .order_by(MedicineBatch.expiry_date)
            .limit(20)
        )
        active_medicines = await self.db_session.scalar(
            select(func.count(Medicine.id)).where(Medicine.is_active.is_(True))
        )
        return {
            "active_medicines": int(active_medicines or 0),
            "low_stock": [
                {"brand_name": b, "generic_name": g, "strength": s, "usable_stock": int(stock)}
                for b, g, s, stock in low_rows.all()
            ],
            "expiring_within_days": expiring_days,
            "expiring_batches": [
                {
                    "brand_name": b,
                    "strength": s,
                    "batch_no": batch_no,
                    "expiry_date": expiry.isoformat(),
                    "quantity_in_stock": int(qty),
                }
                for b, s, batch_no, expiry, qty in expiring_rows.all()
            ],
        }

    async def purchase_summary(self, day: date) -> dict:
        by_status = await self.db_session.execute(
            select(PurchaseOrder.status, func.count(PurchaseOrder.id))
            .where(cast(PurchaseOrder.order_date, Date) == day)
            .group_by(PurchaseOrder.status)
        )
        by_payment = await self.db_session.execute(
            select(PurchaseOrder.payment_status, func.count(PurchaseOrder.id))
            .where(cast(PurchaseOrder.order_date, Date) == day)
            .group_by(PurchaseOrder.payment_status)
        )
        total_amount = await self.db_session.scalar(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).where(
                cast(PurchaseOrder.order_date, Date) == day
            )
        )
        return {
            "date": day.isoformat(),
            "by_status": _counts(by_status.all()),
            "by_payment_status": _counts(by_payment.all()),
            "total_amount": _money(total_amount),
        }

    async def prescription_summary(self, day: date) -> dict:
        by_status = await self.db_session.execute(
            select(Prescription.status, func.count(Prescription.id))
            .where(Prescription.prescription_date == day)
            .group_by(Prescription.status)
        )
        undelivered = await self.db_session.scalar(
            select(
                func.coalesce(
                    func.sum(
                        PrescriptionItem.quantity_prescribed - PrescriptionItem.quantity_delivered
                    ),
                    0,
                )
            )
            .join(Prescription, Prescription.id == PrescriptionItem.prescription_id)
            .where(
                Prescription.status != PrescriptionStatus.CANCELLED,
                PrescriptionItem.dispense_status != DispenseStatus.NOT_AVAILABLE,
            )
        )
        return {
            "date": day.isoformat(),
            "by_status": _counts(by_status.all()),
            "undelivered_quantity": int(undelivered or 0),
        }

    async def daily_overview(self, day: date) -> dict:
        return {
            "patients": await self.patient_summary(day),
            "users": await self.user_summary(),
            "orders": await self.order_summary(day),
            "reports": await self.report_summary(day),
            "sales": await self.sales_summary(day),
            "pharmacy": await self.pharmacy_summary(day),
            "purchases": await self.purchase_summary(day),
            "prescriptions": await self.prescription_summary(day),
        }

    async def medicine_stock(self, query: str, limit: int = 5) -> list[dict]:
        today = date.today()
        usable = (
            select(
                MedicineBatch.medicine_id,
                func.coalesce(func.sum(MedicineBatch.quantity_in_stock), 0).label("stock"),
            )
            .where(
                MedicineBatch.status == MedicineBatchStatus.ACTIVE,
                MedicineBatch.expiry_date >= today,
                MedicineBatch.quantity_in_stock > 0,
            )
            .group_by(MedicineBatch.medicine_id)
            .subquery()
        )
        pattern = f"%{query}%"
        rows = await self.db_session.execute(
            select(
                Medicine.brand_name,
                Medicine.generic_name,
                Medicine.strength,
                Medicine.dosage_form,
                Medicine.selling_price,
                func.coalesce(usable.c.stock, 0),
            )
            .outerjoin(usable, usable.c.medicine_id == Medicine.id)
            .where(
                Medicine.is_active.is_(True),
                or_(
                    Medicine.brand_name.ilike(pattern),
                    Medicine.generic_name.ilike(pattern),
                ),
            )
            .order_by(Medicine.brand_name)
            .limit(limit)
        )
        return [
            {
                "brand_name": brand,
                "generic_name": generic,
                "strength": strength,
                "dosage_form": form.value,
                "selling_price": str(price),
                "usable_stock": int(stock),
                "in_stock": int(stock) > 0,
            }
            for brand, generic, strength, form, price, stock in rows.all()
        ]

    async def my_released_reports(self, patient_id: uuid.UUID, limit: int = 10) -> list[dict]:
        rows = await self.db_session.execute(
            select(
                DiagnosticTestReport.released_at,
                DiagnosticOrderItem.test_code,
                TestCatalogue.test_name,
            )
            .join(DiagnosticOrderItem, DiagnosticOrderItem.id == DiagnosticTestReport.order_item_id)
            .join(DiagnosticOrder, DiagnosticOrder.id == DiagnosticOrderItem.order_id)
            .join(TestCatalogue, TestCatalogue.test_code == DiagnosticOrderItem.test_code)
            .where(
                DiagnosticOrder.patient_id == patient_id,
                DiagnosticTestReport.report_status == ReportStatus.RELEASED,
            )
            .order_by(DiagnosticTestReport.released_at.desc())
            .limit(limit)
        )
        return [
            {
                "test_code": code,
                "test_name": name,
                "released_at": released.isoformat() if released else None,
            }
            for released, code, name in rows.all()
        ]

    async def my_pending_report_count(self, patient_id: uuid.UUID) -> int:
        count = await self.db_session.scalar(
            select(func.count(DiagnosticOrderItem.id))
            .join(DiagnosticOrder, DiagnosticOrder.id == DiagnosticOrderItem.order_id)
            .outerjoin(
                DiagnosticTestReport,
                DiagnosticTestReport.order_item_id == DiagnosticOrderItem.id,
            )
            .where(
                DiagnosticOrder.patient_id == patient_id,
                or_(
                    DiagnosticTestReport.id.is_(None),
                    DiagnosticTestReport.report_status == ReportStatus.DRAFT,
                ),
            )
        )
        return int(count or 0)