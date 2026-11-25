import asyncio
from datetime import date, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.diagnostic_test_catalogue.repositories import (
    DepartmentRepository,
    TestCatalogueRepository,
)
from app.modules.diagnostic_test_catalogue.schemas import DepartmentCreate, TestCreate
from app.modules.diagnostic_test_catalogue.services import (
    DepartmentService,
    TestCatalogueService,
)
from app.modules.medicines.models import DosageForm
from app.modules.medicines.repositories import MedicineRepository
from app.modules.medicines.schemas import MedicineCreate
from app.modules.medicines.services import MedicineService
from app.modules.patients.models import Sex
from app.modules.patients.repositories import PatientRepository
from app.modules.patients.schemas import PatientCreate
from app.modules.patients.services import PatientService
from app.modules.purchases.models import PaymentStatus as PurchasePaymentStatus
from app.modules.purchases.repositories import PurchaseOrderRepository
from app.modules.purchases.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchasePaymentUpdate,
    ReceiveDelivery,
    ReceiveItem,
)
from app.modules.purchases.services import PurchaseOrderService
from app.modules.inventory.repositories import (
    MedicineBatchRepository,
    StockMovementRepository,
)
from app.modules.suppliers.repositories import SupplierRepository
from app.modules.suppliers.schemas import SupplierCreate
from app.modules.suppliers.services import SupplierService
from app.modules.users.models import Role, User
from app.modules.users.repositories import UserRepository
from app.modules.users.schemas import CreateUserStaff, PatientAccountCreate
from app.modules.users.services import UserService

SEED_PASSWORD = "TestPass@123"  # Dummy only. Change before any real use.

# ADMIN = ("Arif", "Hossain", "01711000001", "admin@diagnoflow.com")

STAFF = [
    ("Nusrat", "Jahan", "01711000002", "reception@diagnoflow.com", Role.RECEPTIONIST),
    ("Tanvir", "Ahmed", "01711000003", "lab@diagnoflow.com", Role.LAB_TECHNICIAN),
    ("Farhana", "Akter", "01711000004", "lab2@diagnoflow.com", Role.LAB_TECHNICIAN),
    ("Shakil", "Ahmed", "01711000005", "pharmacy@diagnoflow.com", Role.PHARMACIST),
    ("Rina", "Begum", "01711000006", "pharmacymanager@diagnoflow.com", Role.PHARMACY_MANAGER),
]

# (first, last, sex, age, phone, gets a patient login account)
PATIENTS = [
    ("Abdul", "Karim", Sex.MALE, 45, "01811000001", True),
    ("Fatema", "Begum", Sex.FEMALE, 38, "01811000002", True),
    ("Rakib", "Hasan", Sex.MALE, 29, "01911000003", True),
    ("Sharmin", "Akter", Sex.FEMALE, 26, "01811000004", True),
    ("Kamal", "Uddin", Sex.MALE, 52, "01722000005", False),
    ("Nasrin", "Sultana", Sex.FEMALE, 61, "01922000006", False),
    ("Sajib", "Rahman", Sex.MALE, 34, "01511000007", False),
    ("Lima", "Akter", Sex.FEMALE, 22, "01611000008", False),
    ("Hossain", "Ali", Sex.MALE, 68, "01311000009", False),
    ("Priya", "Das", Sex.FEMALE, 31, "01811000010", False),
]

DEPARTMENTS = [
    "Haematology",
    "Biochemistry",
    "Microbiology",
    "Serology",
    "Radiology",
    "Cardiology",
]

# (code, name, department, price BDT, expected delivery)
TESTS = [
    ("CBC", "Complete Blood Count", "Haematology", "400", "Same day, 6 hours"),
    ("ESR", "Erythrocyte Sedimentation Rate", "Haematology", "150", "Same day, 4 hours"),
    ("BGROUP", "Blood Grouping and Rh Typing", "Haematology", "150", "Same day, 2 hours"),
    ("FBS", "Fasting Blood Sugar", "Biochemistry", "120", "Same day, 3 hours"),
    ("RBS", "Random Blood Sugar", "Biochemistry", "100", "Same day, 2 hours"),
    ("HBA1C", "HbA1c (Glycated Haemoglobin)", "Biochemistry", "650", "Next day"),
    ("LIPID", "Lipid Profile", "Biochemistry", "850", "Same day, 6 hours"),
    ("LFT", "Liver Function Test", "Biochemistry", "750", "Same day, 6 hours"),
    ("KFT", "Kidney Function Test (Creatinine and Urea)", "Biochemistry", "550", "Same day, 6 hours"),
    ("CREAT", "Serum Creatinine", "Biochemistry", "250", "Same day, 4 hours"),
    ("SGPT", "SGPT (ALT)", "Biochemistry", "200", "Same day, 4 hours"),
    ("ELECT", "Serum Electrolytes", "Biochemistry", "450", "Same day, 6 hours"),
    ("VITD", "Vitamin D (25-OH)", "Biochemistry", "1400", "Next day"),
    ("TSH", "Thyroid Stimulating Hormone (TSH)", "Biochemistry", "550", "Next day"),
    ("THYROID", "Thyroid Profile (T3, T4, TSH)", "Biochemistry", "900", "Next day"),
    ("URINE", "Urine Routine Examination", "Microbiology", "200", "Same day, 4 hours"),
    ("STOOL", "Stool Routine Examination", "Microbiology", "200", "Same day, 4 hours"),
    ("CULTURE", "Urine Culture and Sensitivity", "Microbiology", "800", "3 days"),
    ("DENGUE", "Dengue NS1 Antigen", "Microbiology", "600", "Same day, 4 hours"),
    ("WIDAL", "Widal Test", "Microbiology", "350", "Same day, 6 hours"),
    ("HBSAG", "HBsAg (Hepatitis B Surface Antigen)", "Serology", "450", "Same day, 6 hours"),
    ("CRP", "C-Reactive Protein (CRP)", "Serology", "550", "Same day, 6 hours"),
    ("BHCG", "Beta-hCG (Pregnancy Test, Blood)", "Serology", "600", "Same day, 6 hours"),
    ("XRAY-CHEST", "Chest X-Ray (PA View)", "Radiology", "500", "Same day, 2 hours"),
    ("USG-ABD", "USG of Whole Abdomen", "Radiology", "900", "Same day, report in 2 hours"),
    ("USG-PREG", "Pregnancy Profile USG", "Radiology", "800", "Same day, report in 2 hours"),
    ("ECG", "ECG (12 Lead)", "Cardiology", "300", "Same day, 30 minutes"),
    ("ECHO", "Echocardiogram", "Cardiology", "1500", "Same day, report in 2 hours"),
]

# (key, name, phone, email)
SUPPLIERS = [
    ("square", "Square Pharmaceuticals Ltd", "01713000001", "sales@squarepharma.com"),
    ("beximco", "Beximco Pharmaceuticals Ltd", "01713000002", "sales@beximcopharma.com"),
    ("renata", "Renata PLC", "01713000003", "sales@renata.com"),
    ("eskayef", "Eskayef Pharmaceuticals Ltd", "01713000004", "sales@eskayef.com"),
    ("gsk", "GSK Bangladesh Ltd", "01713000005", "sales@gsk.com"),
]

# (brand, generic, strength, form, description, selling price, reorder level, supplier key)
MEDICINES = [
    ("Napa", "Paracetamol", "500mg", DosageForm.TABLET, "Paracetamol 500mg tablet. For fever and pain.", "1.50", 100, "beximco"),
    ("Napa Extra", "Paracetamol + Caffeine", "500mg+65mg", DosageForm.TABLET, "Paracetamol with caffeine for pain and fever.", "2.50", 50, "beximco"),
    ("Ace", "Paracetamol", "500mg", DosageForm.TABLET, "Paracetamol 500mg tablet. For fever and pain.", "1.50", 100, "square"),
    ("Seclo", "Omeprazole", "20mg", DosageForm.CAPSULE, "Omeprazole capsule for acidity and gastric ulcer.", "7.00", 50, "square"),
    ("Maxpro", "Esomeprazole", "20mg", DosageForm.CAPSULE, "Esomeprazole capsule for acidity and reflux.", "8.00", 50, "renata"),
    ("Sergel", "Esomeprazole", "20mg", DosageForm.CAPSULE, "Esomeprazole capsule for acidity and reflux.", "7.50", 50, "eskayef"),
    ("Fexo", "Fexofenadine Hydrochloride", "120mg", DosageForm.TABLET, "Anti-allergy tablet for sneezing and itching.", "9.00", 50, "square"),
    ("Alatrol", "Cetirizine Hydrochloride", "10mg", DosageForm.TABLET, "Anti-allergy tablet for cold and allergy.", "3.00", 100, "square"),
    ("Zimax", "Azithromycin", "500mg", DosageForm.TABLET, "Antibiotic tablet. Take only as prescribed.", "35.00", 30, "square"),
    ("Azicin", "Azithromycin", "500mg", DosageForm.TABLET, "Antibiotic tablet. Take only as prescribed.", "32.00", 30, "beximco"),
    ("Ciprocin", "Ciprofloxacin", "500mg", DosageForm.TABLET, "Antibiotic tablet. Take only as prescribed.", "12.00", 50, "square"),
    ("Fimoxyl", "Amoxicillin", "500mg", DosageForm.CAPSULE, "Antibiotic capsule. Take only as prescribed.", "9.00", 50, "square"),
    ("Comet", "Metformin Hydrochloride", "500mg", DosageForm.TABLET, "Tablet for type 2 diabetes.", "3.50", 100, "square"),
    ("Amlocard", "Amlodipine", "5mg", DosageForm.TABLET, "Tablet for high blood pressure.", "5.00", 50, "square"),
    ("Losartil", "Losartan Potassium", "50mg", DosageForm.TABLET, "Tablet for high blood pressure.", "7.00", 50, "square"),
    ("Atova", "Atorvastatin", "10mg", DosageForm.TABLET, "Tablet for high cholesterol.", "10.00", 30, "beximco"),
    ("Montair", "Montelukast Sodium", "10mg", DosageForm.TABLET, "Tablet for asthma and allergy.", "15.00", 30, "square"),
    ("Pantonix", "Pantoprazole", "40mg", DosageForm.TABLET, "Tablet for acidity and gastric ulcer.", "12.00", 30, "square"),
    ("Emistat", "Ondansetron", "8mg", DosageForm.TABLET, "Tablet for nausea and vomiting.", "10.00", 20, "square"),
    ("Motigut", "Domperidone", "10mg", DosageForm.TABLET, "Tablet for nausea and stomach fullness.", "4.00", 50, "eskayef"),
    ("Azmasol", "Salbutamol", "100mcg/dose", DosageForm.OTHER, "Salbutamol inhaler for asthma.", "220.00", 20, "beximco"),
    ("Napa Syrup", "Paracetamol", "120mg/5ml", DosageForm.SYRUP, "Paracetamol syrup for children with fever.", "35.00", 30, "beximco"),
    ("Alatrol Syrup", "Cetirizine Hydrochloride", "5mg/5ml", DosageForm.SYRUP, "Cetirizine syrup for allergy in children.", "45.00", 30, "square"),
    ("Betnovate", "Betamethasone Valerate", "0.1%", DosageForm.CREAM, "Steroid cream for skin inflammation. External use only.", "65.00", 20, "gsk"),
    ("Ciprocin Drops", "Ciprofloxacin", "0.3%", DosageForm.DROPS, "Antibiotic eye drops. Take only as prescribed.", "55.00", 20, "square"),
    ("Doxin", "Doxycycline", "100mg", DosageForm.CAPSULE, "Antibiotic capsule. Take only as prescribed.", "6.00", 50, "renata"),
    ("D-Rise", "Cholecalciferol (Vitamin D3)", "20000 IU", DosageForm.CAPSULE, "Vitamin D3 capsule for vitamin D deficiency.", "35.00", 20, "renata"),
]

# (supplier key, batch prefix, [(brand, qty ordered, unit cost, qty received, expiry in days)])
# qty received None means: do not receive this order at all.
PURCHASES = [
    ("square", "SQ", [
        ("Ace", 200, "1.00", 200, 540),
        ("Seclo", 100, "5.00", 100, 540),
        ("Fexo", 100, "6.50", 100, 540),
        ("Alatrol", 100, "2.00", 100, 40),  # Expiring soon, on purpose.
        ("Zimax", 50, "26.00", 50, 540),
        ("Ciprocin", 100, "8.50", 100, 540),
        ("Fimoxyl", 100, "6.50", 100, 540),
        ("Comet", 200, "2.50", 200, 540),
        ("Amlocard", 100, "3.50", 100, 540),
        ("Losartil", 100, "5.00", 100, 540),
        ("Montair", 50, "11.00", 50, 540),
        ("Pantonix", 50, "9.00", 50, 540),
        ("Emistat", 20, "7.00", 20, 540),  # At reorder level, on purpose.
        ("Alatrol Syrup", 30, "32.00", 30, 540),
        ("Ciprocin Drops", 20, "40.00", 20, 540),
    ], PurchasePaymentStatus.PAID),
    ("beximco", "BX", [
        ("Napa", 300, "1.00", 150, 540),  # Partly received, on purpose.
        ("Napa Extra", 100, "1.80", 100, 540),
        ("Azicin", 50, "24.00", 50, 540),
        ("Atova", 50, "7.50", 50, 540),
        ("Azmasol", 20, "160.00", 20, 540),
        ("Napa Syrup", 30, "25.00", 30, 540),
    ], PurchasePaymentStatus.PARTIALLY_PAID),
    ("renata", "RN", [
        ("Maxpro", 100, "5.50", None, 540),
        ("Doxin", 100, "4.50", None, 540),
        ("D-Rise", 40, "25.00", None, 540),
    ], None),
    ("eskayef", "ES", [
        ("Sergel", 100, "5.50", 100, 540),
        ("Motigut", 100, "3.00", 100, 540),
    ], PurchasePaymentStatus.PAID),
    ("gsk", "GS", [
        ("Betnovate", 20, "48.00", None, 540),
    ], None),
]


async def main() -> None:
    async with SessionLocal() as session:
        try:
            user_repo = UserRepository(session)
            patient_repo = PatientRepository(session)
            dept_repo = DepartmentRepository(session)
            test_repo = TestCatalogueRepository(session)
            supplier_repo = SupplierRepository(session)
            medicine_repo = MedicineRepository(session)
            purchase_repo = PurchaseOrderRepository(session)
            batch_repo = MedicineBatchRepository(session)
            movement_repo = StockMovementRepository(session)

            user_service = UserService(user_repo, patient_repo)
            patient_service = PatientService(patient_repo)
            dept_service = DepartmentService(dept_repo)
            test_service = TestCatalogueService(test_repo, dept_repo)
            supplier_service = SupplierService(supplier_repo)
            medicine_service = MedicineService(medicine_repo)
            purchase_service = PurchaseOrderService(
                purchase_repo, supplier_repo, medicine_repo, batch_repo, movement_repo
            )

            # --- Users ---
            for first, last, mobile, email, role in STAFF:
                if await user_repo.get_by_mobile_number(mobile) is None:
                    await user_service.register_user(CreateUserStaff(
                        first_name=first, last_name=last, mobile_number=mobile,
                        email=email, password=SEED_PASSWORD, role=role,
                    ))
                    print(f"Created staff {first} {last} ({role.value})")

            # --- Patients + patient login accounts ---
            for first, last, sex, age, phone, has_account in PATIENTS:
                patient = await patient_repo.get_by_phone(phone)
                if patient is None:
                    created = await patient_service.create_patient(PatientCreate(
                        patient_first_name=first, patient_last_name=last,
                        sex=sex, age=age, phone_number=phone,
                    ))
                    patient_id = created.id
                    print(f"Created patient {created.patient_no} {first} {last}")
                else:
                    patient_id = patient.id
                if has_account and await user_repo.get_by_patient_id(patient_id) is None:
                    await user_service.create_patient_account(PatientAccountCreate(
                        username=phone, password=SEED_PASSWORD,
                    ))
                    print(f"Created patient account for {first} {last}")

            # --- Departments and tests ---
            dept_ids = {}
            for name in DEPARTMENTS:
                existing = await dept_repo.get_by_name(name)
                if existing is None:
                    created = await dept_service.create_department(DepartmentCreate(name=name))
                    dept_ids[name] = created.id
                else:
                    dept_ids[name] = existing.id
            for code, name, dept, price, delivery in TESTS:
                if await test_repo.get_by_code(code) is None:
                    await test_service.create_test(TestCreate(
                        test_code=code, test_name=name, department_id=dept_ids[dept],
                        price=Decimal(price), expected_delivery_time=delivery,
                    ))
            print(f"Departments and {len(TESTS)} tests ready")

            # --- Suppliers ---
            supplier_ids = {}
            for key, name, phone, email in SUPPLIERS:
                existing = await supplier_repo.get_by_phone(phone)
                if existing is None:
                    created = await supplier_service.create_supplier(SupplierCreate(
                        supplier_name=name, phone=phone, email=email,
                    ))
                    supplier_ids[key] = created.id
                else:
                    supplier_ids[key] = existing.id

            # --- Medicines ---
            medicine_ids = {}
            for brand, generic, strength, form, desc, price, reorder, _key in MEDICINES:
                existing = await medicine_repo.get_by_identity(brand, strength, form)
                if existing is None:
                    created = await medicine_service.create_medicine(MedicineCreate(
                        brand_name=brand, generic_name=generic, strength=strength,
                        dosage_form=form, description=desc,
                        selling_price=Decimal(price), reorder_level=reorder,
                    ))
                    medicine_ids[brand] = created.id
                else:
                    medicine_ids[brand] = existing.id
            print(f"{len(MEDICINES)} medicines ready")

            # --- Purchases (opening stock) ---
            _, existing_purchases = await purchase_repo.search(
                None, None, None, None, None, None, 1, 1
            )
            if existing_purchases == 0:
                for supplier_key, prefix, items, pay_status in PURCHASES:
                    order = await purchase_service.create_order(PurchaseOrderCreate(
                        supplier_id=supplier_ids[supplier_key],
                        expected_delivery=date.today() + timedelta(days=7),
                        items=[
                            PurchaseOrderItemCreate(
                                medicine_id=medicine_ids[brand],
                                quantity_ordered=qty,
                                unit_cost=Decimal(cost),
                            )
                            for brand, qty, cost, _recv, _exp in items
                        ],
                    ), created_by=(await user_repo.get_by_mobile_number(STAFF[4][2])).id)
                    receive_items = []
                    for idx, (brand, _qty, _cost, received, expiry_days) in enumerate(items, start=1):
                        if received is None:
                            continue
                        item_id = next(
                            item.id for item in order.items
                            if item.medicine.id == medicine_ids[brand]
                        )
                        receive_items.append(ReceiveItem(
                            purchase_order_item_id=item_id,
                            quantity_received=received,
                            batch_no=f"{prefix}-{idx:02d}",
                            expiry_date=date.today() + timedelta(days=expiry_days),
                        ))
                    if receive_items:
                        order = await purchase_service.receive_delivery(
                            order.id, ReceiveDelivery(items=receive_items),
                            received_by=(await user_repo.get_by_mobile_number(STAFF[4][2])).id,
                        )
                    if pay_status is not None:
                        await purchase_service.update_payment(
                            order.id, PurchasePaymentUpdate(payment_status=pay_status)
                        )
                    print(f"Created purchase {order.purchase_no} ({order.status.value})")
            else:
                print("Purchases already exist, skipping opening stock")

            await session.commit()
            print("\nMaster data seeded.")
            print(f"Login password for every seed account: {SEED_PASSWORD}")
            print(f"Receptionist: {STAFF[0][2]} | "
                  f"Lab: {STAFF[1][2]} | Pharmacist: {STAFF[3][2]} | "
                  f"Pharmacy manager: {STAFF[4][2]}")
            print("Patient logins (mobile = patient phone): 01811000001, 01811000002, "
                  "01911000003, 01811000004")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())