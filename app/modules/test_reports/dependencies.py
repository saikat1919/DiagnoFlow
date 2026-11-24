from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.test_reports.repositories import TestReportRepository
from app.modules.test_reports.services import TestReportService
from app.modules.diagnostic_orders.dependencies import DiagnosticOrderRepositoryDep
from app.modules.diagnostic_orders.repositories import DiagnosticOrderRepository

def get_test_report_repository(session: SessionDep) -> TestReportRepository:
    return TestReportRepository(session)

TestReportRepositoryDep = Annotated[TestReportRepository, Depends(get_test_report_repository)]

def get_test_report_service(
    repo: TestReportRepositoryDep,
    order_repo: DiagnosticOrderRepositoryDep,
) -> TestReportService:
    return TestReportService(repo, order_repo)

TestReportServiceDep = Annotated[TestReportService, Depends(get_test_report_service)]