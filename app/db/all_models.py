"""Import all models here"""
from app.modules.users.models import User
from app.modules.diagnostic_test_catalogue.models import Department, TestCatalogue
from app.modules.patients.models import Patient
from app.modules.diagnostic_orders.models import DiagnosticOrder, DiagnosticOrderItem
from app.modules.test_reports.models import DiagnosticTestReport
from app.modules.medicines.models import Medicine