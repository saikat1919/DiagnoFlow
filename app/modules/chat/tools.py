import json
from datetime import date
from typing import Any
from app.core.exceptions.errors import ForbiddenError
from app.integrations.llm.base import ToolSpec
from app.modules.chat.summaries import SummaryRepository
from app.modules.knowledge.schemas import SearchMode, Source
from app.modules.knowledge.services import KnowledgeService
from app.modules.users.models import Role, User

DATE_PARAM = {
    "type": "string",
    "description": "Date as YYYY-MM-DD. Leave it out for today.",
}

def _tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=description,
        parameters={"type": "object", "properties": properties or {}, "required": required or []},
    )

GET_DAILY_OVERVIEW = _tool(
    "get_daily_overview",
    "Summary of every part of the centre for one day: patients, orders, reports, sales, pharmacy, purchases and prescriptions. Counts and money only, no personal information.",
    {"date": DATE_PARAM},
)
GET_PATIENT_SUMMARY = _tool(
    "get_patient_summary",
    "How many patients registered on one day and how many patients there are in total. Counts only.",
    {"date": DATE_PARAM},
)
GET_USER_SUMMARY = _tool(
    "get_user_summary",
    "How many user accounts there are by role and how many are active. Counts only.",
)
GET_ORDER_SUMMARY = _tool(
    "get_order_summary",
    "Diagnostic orders for one day by work status and payment status, with the total amount. Counts and money only.",
    {"date": DATE_PARAM},
)
GET_REPORT_SUMMARY = _tool(
    "get_report_summary",
    "Test reports by status and how many were released on one day. Counts only.",
    {"date": DATE_PARAM},
)
GET_SALES_SUMMARY = _tool(
    "get_sales_summary",
    "Medicine sales for one day: how many sales, total amount and paid amount, by payment status. Counts and money only.",
    {"date": DATE_PARAM},
)
GET_PHARMACY_SUMMARY = _tool(
    "get_pharmacy_summary",
    "Pharmacy stock: medicines below reorder level and batches expiring soon. Medicine and batch details only, no patient information.",
    {"days": {"type": "integer", "description": "How many days ahead to look for expiring batches. Default 30."}},
)
GET_PURCHASE_SUMMARY = _tool(
    "get_purchase_summary",
    "Medicine purchases for one day by order status and payment status, with the total amount. Counts and money only.",
    {"date": DATE_PARAM},
)
GET_PRESCRIPTION_SUMMARY = _tool(
    "get_prescription_summary",
    "Prescriptions for one day by status and how much medicine is still undelivered in total. Counts only.",
    {"date": DATE_PARAM},
)
GET_MY_REPORT_UPDATES = _tool(
    "get_my_report_updates",
    "The caller's own released test reports and how many of their reports are still in preparation. Only the caller's own reports.",
)
SEARCH_MEDICINES = _tool(
    "search_medicines",
    "Search the pharmacy for medicines by brand or generic name. Returns the name, strength, price and whether each is in stock.",
    {"query": {"type": "string", "description": "Brand or generic name, e.g. 'napa' or 'paracetamol'."}},
    ["query"],
)
SEARCH_POLICIES = _tool(
    "search_policies",
    "Search the centre's company policies. Returns the 3 most relevant policy sections.",
    {"query": {"type": "string", "description": "What to look for, as a short question."}},
    ["query"],
)
SEARCH_TESTS = _tool(
    "search_tests",
    "Search the test catalogue by test name or code. Returns the test name, price and expected delivery time.",
    {"query": {"type": "string", "description": "Test name or code, e.g. 'CBC'."}},
    ["query"],
)

_TOOLS_FOR_ROLE: dict[Role, list[ToolSpec]] = {
    Role.SYSTEM_ADMIN: [
        GET_DAILY_OVERVIEW, GET_PATIENT_SUMMARY, GET_USER_SUMMARY, GET_ORDER_SUMMARY,
        GET_REPORT_SUMMARY, GET_SALES_SUMMARY, GET_PHARMACY_SUMMARY, GET_PURCHASE_SUMMARY,
        GET_PRESCRIPTION_SUMMARY, SEARCH_MEDICINES, SEARCH_POLICIES, SEARCH_TESTS,
    ],
    Role.RECEPTIONIST: [
        GET_PATIENT_SUMMARY, GET_ORDER_SUMMARY, GET_REPORT_SUMMARY,
        SEARCH_MEDICINES, SEARCH_POLICIES, SEARCH_TESTS,
    ],
    Role.LAB_TECHNICIAN: [
        GET_ORDER_SUMMARY, GET_REPORT_SUMMARY, SEARCH_POLICIES, SEARCH_TESTS,
    ],
    Role.PHARMACIST: [
        GET_PHARMACY_SUMMARY, GET_SALES_SUMMARY,
        GET_PRESCRIPTION_SUMMARY, SEARCH_MEDICINES, SEARCH_POLICIES, SEARCH_TESTS,
    ],
    Role.PHARMACY_MANAGER: [
        GET_PHARMACY_SUMMARY, GET_SALES_SUMMARY, GET_PURCHASE_SUMMARY,
        GET_PRESCRIPTION_SUMMARY, SEARCH_MEDICINES, SEARCH_POLICIES, SEARCH_TESTS,
    ],
    Role.PATIENT: [
        GET_MY_REPORT_UPDATES, SEARCH_MEDICINES, SEARCH_POLICIES, SEARCH_TESTS,
    ],
}


def tools_for_role(role: Role) -> list[ToolSpec]:
    return list(_TOOLS_FOR_ROLE[role])


def _parse_date(args: dict[str, Any]) -> date:
    raw = args.get("date")
    if raw is None or str(raw).strip() == "":
        return date.today()
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc


async def execute_tool(
    summaries: SummaryRepository,
    knowledge: KnowledgeService,
    user: User,
    name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    allowed = {spec.name for spec in tools_for_role(user.role)}
    if name not in allowed:
        return {"error": "This tool is not available for your role"}
    try:
        if name == "get_daily_overview":
            return await summaries.daily_overview(_parse_date(args))
        if name == "get_patient_summary":
            return await summaries.patient_summary(_parse_date(args))
        if name == "get_user_summary":
            return await summaries.user_summary()
        if name == "get_order_summary":
            return await summaries.order_summary(_parse_date(args))
        if name == "get_report_summary":
            return await summaries.report_summary(_parse_date(args))
        if name == "get_sales_summary":
            return await summaries.sales_summary(_parse_date(args))
        if name == "get_pharmacy_summary":
            days = args.get("days") or 30
            return await summaries.pharmacy_summary(date.today(), int(days))
        if name == "get_purchase_summary":
            return await summaries.purchase_summary(_parse_date(args))
        if name == "get_prescription_summary":
            return await summaries.prescription_summary(_parse_date(args))
        if name == "get_my_report_updates":
            if user.patient_id is None:
                raise ForbiddenError("Only patient accounts have report updates")
            return {
                "released_reports": await summaries.my_released_reports(user.patient_id),
                "reports_in_preparation": await summaries.my_pending_report_count(user.patient_id),
            }
        if name == "search_medicines":
            query = args["query"]
            hits = await knowledge.search(query, SearchMode.HYBRID, Source.MEDICINE, limit=3)
            return {
                "sections": [{"title": h.title, "text": h.content} for h in hits],
                "stock": await summaries.medicine_stock(query),
            }
        if name == "search_policies":
            hits = await knowledge.search(args["query"], SearchMode.HYBRID, Source.POLICY, limit=3)
            return {"sections": [{"title": h.title, "text": h.content} for h in hits]}
        if name == "search_tests":
            hits = await knowledge.search(args["query"], SearchMode.HYBRID, Source.TEST, limit=3)
            return {"sections": [{"title": h.title, "text": h.content} for h in hits]}
        return {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        return {"error": str(exc) or exc.__class__.__name__}