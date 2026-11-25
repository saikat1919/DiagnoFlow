from fastapi import APIRouter
from app.modules.users.controllers import auth_router, user_router
from app.modules.patients.controllers import patient_router
from app.modules.medicines.controllers import medicine_router
from app.modules.suppliers.controllers import supplier_router
from app.modules.diagnostic_test_catalogue.controllers import department_router, test_router
from app.modules.diagnostic_orders.controllers import diagnostic_order_router
from app.modules.test_reports.controllers import test_report_router
from app.modules.inventory.controllers import inventory_router
from app.modules.purchases.controllers import purchase_router
from app.modules.prescriptions.controllers import prescription_router
from app.modules.sales.controllers import sale_router
from app.modules.knowledge.controllers import knowledge_router
from app.modules.chat.controllers import chat_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(patient_router)
api_router.include_router(user_router)
api_router.include_router(medicine_router)
api_router.include_router(supplier_router)
api_router.include_router(department_router)
api_router.include_router(test_router)
api_router.include_router(diagnostic_order_router)
api_router.include_router(test_report_router)
api_router.include_router(inventory_router)
api_router.include_router(purchase_router)
api_router.include_router(prescription_router)
api_router.include_router(sale_router)
api_router.include_router(knowledge_router)
api_router.include_router(chat_router)