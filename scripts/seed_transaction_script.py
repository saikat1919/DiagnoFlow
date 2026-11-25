"""Seed demo transactions on top of scripts/seed_master_data.py.

Creates diagnostic orders in every work status, draft and released
reports, prescriptions in every dispense state, one damaged-stock
movement, and walk-in plus prescription sales. Runs only when no
diagnostic orders exist yet, so it cannot double-sell stock.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.db.session import SessionLocal
from app.modules.diagnostic_orders.models import PaymentStatus as OrderPaymentStatus
from app.modules.diagnostic_orders.models import WorkStatus
from app.modules.diagnostic_orders.repositories import DiagnosticOrderRepository
from app.modules.diagnostic_orders.schemas import (
    OrderCreate,
    OrderItemCreate,
    OrderItemStatusUpdate,
    OrderPaymentUpdate,
    OrderStatusUpdate,
)
from app.modules.diagnostic_orders.services import DiagnosticOrderService
from app.modules.diagnostic_test_catalogue.repositories import TestCatalogueRepository
from app.modules.inventory.models import MovementType
from app.modules.inventory.repositories import MedicineBatchRepository, StockMovementRepository
from app.modules.inventory.schemas import StockMovementCreate
from app.modules.inventory.services import StockMovementService
from app.modules.medicines.models import DosageForm
from app.modules.medicines.repositories import MedicineRepository
from app.modules.patients.repositories import PatientRepository
from app.modules.prescriptions.repositories import PrescriptionRepository
from app.modules.prescriptions.schemas import (
    PrescriptionCreate,
    PrescriptionItemCreate,
    PrescriptionItemMatch,
)
from app.modules.prescriptions.services import PrescriptionService
from app.modules.sales.models import PaymentMethod
from app.modules.sales.models import PaymentStatus as SalePaymentStatus
from app.modules.sales.repositories import SalesRepository
from app.modules.sales.schemas import SaleCreate, SaleItemCreate
from app.modules.sales.services import SaleService
from app.modules.test_reports.repositories import TestReportRepository
from app.modules.test_reports.schemas import ReportCreate
from app.modules.test_reports.services import TestReportService
from app.modules.users.repositories import UserRepository

SEED_PATIENT_PHONES = {
    "abdul": "01811000001",
    "fatema": "01811000002",
    "rakib": "01911000003",
    "sharmin": "01811000004",
    "kamal": "01722000005",
    "nasrin": "01922000006",
}


async def set_order_status(service, order_id, *statuses):
    for status in statuses:
        await service.update_order_status(order_id, OrderStatusUpdate(status=status))


async def set_item_status(service, item_id, *statuses):
    for status in statuses:
        await service.update_order_item_status(
            item_id, OrderItemStatusUpdate(item_status=status)
        )


async def main() -> None:
    async with SessionLocal() as session:
        try:
            user_repo = UserRepository(session)
            patient_repo = PatientRepository(session)
            test_repo = TestCatalogueRepository(session)
            medicine_repo = MedicineRepository(session)
            batch_repo = MedicineBatchRepository(session)
            movement_repo = StockMovementRepository(session)

            order_service = DiagnosticOrderService(
                DiagnosticOrderRepository(session), patient_repo, test_repo
            )
            report_service = TestReportService(
                TestReportRepository(session), DiagnosticOrderRepository(session)
            )
            prescription_service = PrescriptionService(
                PrescriptionRepository(session), patient_repo, medicine_repo
            )
            sale_service = SaleService(
                SalesRepository(session), medicine_repo, batch_repo,
                movement_repo, patient_repo, prescription_service,
            )
            movement_service = StockMovementService(movement_repo, batch_repo)

            _, order_count = await DiagnosticOrderRepository(session).search(
                None, None, None, None, 1, 1
            )
            if order_count > 0:
                print("Diagnostic orders already exist, skipping demo transactions")
                return

            receptionist = await user_repo.get_by_mobile_number("01711000002")
            lab_tech = await user_repo.get_by_mobile_number("01711000003")
            pharmacist = await user_repo.get_by_mobile_number("01711000005")
            manager = await user_repo.get_by_mobile_number("01711000006")
            patients = {
                key: await patient_repo.get_by_phone(phone)
                for key, phone in SEED_PATIENT_PHONES.items()
            }

            async def medicine(brand, strength, form):
                found = await medicine_repo.get_by_identity(brand, strength, form)
                assert found is not None, f"Missing medicine: {brand} {strength}"
                return found

            # --- 1. Completed order, paid, one report released, one draft ---
            order1 = await order_service.create_order(OrderCreate(
                patient_id=patients["abdul"].id,
                expected_delivery=datetime.now(UTC) + timedelta(days=1),
                items=[OrderItemCreate(test_code="CBC"), OrderItemCreate(test_code="FBS")],
            ), created_by=receptionist.id)
            await set_order_status(order_service, order1.id,
                                   WorkStatus.SAMPLE_COLLECTED, WorkStatus.PROCESSING, WorkStatus.COMPLETED)
            for item in order1.items:
                await set_item_status(order_service, item.id,
                                      WorkStatus.SAMPLE_COLLECTED, WorkStatus.PROCESSING, WorkStatus.COMPLETED)
            await order_service.update_order_payment(
                order1.id, OrderPaymentUpdate(payment_status=OrderPaymentStatus.PAID))
            cbc_item = next(i for i in order1.items if i.test.test_code == "CBC")
            fbs_item = next(i for i in order1.items if i.test.test_code == "FBS")
            released = await report_service.create_report(ReportCreate(
                order_item_id=cbc_item.id, file_location="reports/seed/cbc-abdul-karim.pdf",
            ), uploaded_by=lab_tech.id)
            await report_service.release_report(released.id)
            await report_service.create_report(ReportCreate(
                order_item_id=fbs_item.id, file_location="reports/seed/fbs-abdul-karim.pdf",
            ), uploaded_by=lab_tech.id)
            print(f"Order {order1.invoice_no}: completed, CBC report released, FBS report draft")

            # --- 2. Sample collected, unpaid, no reports yet ---
            order2 = await order_service.create_order(OrderCreate(
                patient_id=patients["fatema"].id,
                items=[OrderItemCreate(test_code="HBA1C"), OrderItemCreate(test_code="LIPID")],
            ), created_by=receptionist.id)
            await set_order_status(order_service, order2.id, WorkStatus.SAMPLE_COLLECTED)
            for item in order2.items:
                await set_item_status(order_service, item.id, WorkStatus.SAMPLE_COLLECTED)
            print(f"Order {order2.invoice_no}: sample collected, payment pending")

            # --- 3. Just registered, unpaid ---
            order3 = await order_service.create_order(OrderCreate(
                patient_id=patients["rakib"].id,
                items=[OrderItemCreate(test_code="ECG"), OrderItemCreate(test_code="XRAY-CHEST")],
            ), created_by=receptionist.id)
            print(f"Order {order3.invoice_no}: registered")

            # --- 4. Processing, paid, one report released ---
            order4 = await order_service.create_order(OrderCreate(
                patient_id=patients["sharmin"].id,
                items=[OrderItemCreate(test_code="CBC"), OrderItemCreate(test_code="DENGUE")],
            ), created_by=receptionist.id)
            await set_order_status(order_service, order4.id,
                                   WorkStatus.SAMPLE_COLLECTED, WorkStatus.PROCESSING)
            cbc4 = next(i for i in order4.items if i.test.test_code == "CBC")
            dengue4 = next(i for i in order4.items if i.test.test_code == "DENGUE")
            await set_item_status(order_service, cbc4.id,
                                  WorkStatus.SAMPLE_COLLECTED, WorkStatus.PROCESSING, WorkStatus.COMPLETED)
            await set_item_status(order_service, dengue4.id,
                                  WorkStatus.SAMPLE_COLLECTED, WorkStatus.PROCESSING)
            await order_service.update_order_payment(
                order4.id, OrderPaymentUpdate(payment_status=OrderPaymentStatus.PAID))
            released4 = await report_service.create_report(ReportCreate(
                order_item_id=cbc4.id, file_location="reports/seed/cbc-sharmin-akter.pdf",
            ), uploaded_by=lab_tech.id)
            await report_service.release_report(released4.id)
            print(f"Order {order4.invoice_no}: processing, CBC report released")

            # --- 5. Cancelled order ---
            order5 = await order_service.create_order(OrderCreate(
                patient_id=patients["kamal"].id,
                items=[OrderItemCreate(test_code="TSH"), OrderItemCreate(test_code="VITD")],
            ), created_by=receptionist.id)
            await set_order_status(order_service, order5.id, WorkStatus.CANCELLED)
            print(f"Order {order5.invoice_no}: cancelled")

            # --- Prescriptions ---
            napa = await medicine("Napa", "500mg", DosageForm.TABLET)
            seclo = await medicine("Seclo", "20mg", DosageForm.CAPSULE)
            fexo = await medicine("Fexo", "120mg", DosageForm.TABLET)
            zimax = await medicine("Zimax", "500mg", DosageForm.TABLET)
            napa_extra = await medicine("Napa Extra", "500mg+65mg", DosageForm.TABLET)
            comet = await medicine("Comet", "500mg", DosageForm.TABLET)
            amlocard = await medicine("Amlocard", "5mg", DosageForm.TABLET)

            rx_abdul = await prescription_service.create_prescription(PrescriptionCreate(
                patient_id=patients["abdul"].id, prescriber_name="Dr. Mahmud Hasan",
                prescription_date=date.today(), notes="After food",
                items=[
                    PrescriptionItemCreate(medicine_name="Napa", strength="500mg",
                                           instructions="1 tablet 3 times daily", quantity_prescribed=20),
                    PrescriptionItemCreate(medicine_name="Seclo", strength="20mg",
                                           instructions="1 capsule before breakfast", quantity_prescribed=14),
                ],
            ), recorded_by=receptionist.id)
            for item, med in zip(rx_abdul.items, [napa, seclo]):
                await prescription_service.match_item(
                    item.id, PrescriptionItemMatch(medicine_id=med.id))

            rx_fatema = await prescription_service.create_prescription(PrescriptionCreate(
                patient_id=patients["fatema"].id, prescriber_name="Dr. Sharmin Sultana",
                prescription_date=date.today(), notes=None,
                items=[
                    PrescriptionItemCreate(medicine_name="Fexo", strength="120mg",
                                           instructions="1 tablet daily", quantity_prescribed=10),
                    PrescriptionItemCreate(medicine_name="Vitamin D3", strength="20000 IU",
                                           instructions="1 capsule weekly", quantity_prescribed=4),
                ],
            ), recorded_by=receptionist.id)
            await prescription_service.match_item(
                rx_fatema.items[0].id, PrescriptionItemMatch(medicine_id=fexo.id))
            await prescription_service.mark_item_not_available(rx_fatema.items[1].id)

            rx_rakib = await prescription_service.create_prescription(PrescriptionCreate(
                patient_id=patients["rakib"].id, prescriber_name="Dr. Kamrul Islam",
                prescription_date=date.today(), notes=None,
                items=[
                    PrescriptionItemCreate(medicine_name="Zimax", strength="500mg",
                                           instructions="1 tablet daily for 6 days", quantity_prescribed=6),
                    PrescriptionItemCreate(medicine_name="Napa Extra", strength="500mg+65mg",
                                           instructions="1 tablet twice daily", quantity_prescribed=10),
                ],
            ), recorded_by=receptionist.id)
            await prescription_service.match_item(
                rx_rakib.items[0].id, PrescriptionItemMatch(medicine_id=zimax.id))
            await prescription_service.match_item(
                rx_rakib.items[1].id, PrescriptionItemMatch(medicine_id=napa_extra.id))

            await prescription_service.create_prescription(PrescriptionCreate(
                patient_id=patients["nasrin"].id, prescriber_name="Dr. Mahmud Hasan",
                prescription_date=date.today(), notes="Monthly medicines",
                items=[
                    PrescriptionItemCreate(medicine_name="Comet", strength="500mg",
                                           instructions="1 tablet twice daily", quantity_prescribed=30),
                    PrescriptionItemCreate(medicine_name="Amlocard", strength="5mg",
                                           instructions="1 tablet daily", quantity_prescribed=30),
                ],
            ), recorded_by=receptionist.id)
            print("Prescriptions created: dispensed-ready, not-available, partially-matched, pending")

            # --- One damaged-stock movement, before the sales ---
            alatrol = await medicine("Alatrol", "10mg", DosageForm.TABLET)
            batches, _ = await batch_repo.search(alatrol.id, None, None, True, 1, 1)
            await movement_service.create_movement(StockMovementCreate(
                batch_id=batches[0].id, movement_type=MovementType.DAMAGED, quantity=-2,
            ), created_by=manager.id)
            print("Recorded 2 damaged Alatrol tablets")

            # --- Sales ---
            walk_in = await sale_service.create_sale(SaleCreate(
                patient_id=None, prescription_id=None,
                items=[
                    SaleItemCreate(medicine_id=napa.id, quantity=10),
                    SaleItemCreate(medicine_id=alatrol.id, quantity=5),
                ],
                discount=Decimal("0"), payment_method=PaymentMethod.CASH,
                payment_status=SalePaymentStatus.PAID,
            ), sold_by=pharmacist.id)

            rx_sale = await sale_service.create_sale(SaleCreate(
                patient_id=patients["abdul"].id, prescription_id=rx_abdul.id,
                items=[
                    SaleItemCreate(medicine_id=napa.id, quantity=20),
                    SaleItemCreate(medicine_id=seclo.id, quantity=14),
                ],
                discount=Decimal("10.00"), payment_method=PaymentMethod.BKASH,
                payment_status=SalePaymentStatus.PAID,
            ), sold_by=pharmacist.id)

            await sale_service.create_sale(SaleCreate(
                patient_id=patients["rakib"].id, prescription_id=rx_rakib.id,
                items=[SaleItemCreate(medicine_id=zimax.id, quantity=6)],
                discount=Decimal("0"), payment_method=None,
                payment_status=SalePaymentStatus.PENDING,
            ), sold_by=pharmacist.id)

            await sale_service.create_sale(SaleCreate(
                patient_id=patients["sharmin"].id, prescription_id=None,
                items=[SaleItemCreate(medicine_id=fexo.id, quantity=5)],
                discount=Decimal("0"), payment_method=PaymentMethod.CARD,
                payment_status=SalePaymentStatus.PAID,
            ), sold_by=pharmacist.id)
            print(f"Sales created, including walk-in {walk_in.sale_no} and "
                  f"prescription sale {rx_sale.sale_no}")

            await session.commit()
            print("\nDemo transactions seeded.")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())