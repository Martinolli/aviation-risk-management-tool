from app.api.audit_logs import router as audit_logs_router
from app.api.committees import router as committees_router
from app.api.committee_members import router as committee_members_router
from app.api.health import router as health_router
from app.api.risk_actions import router as risk_actions_router
from app.api.risk_assessments import router as risk_assessments_router
from app.api.risk_decisions import router as risk_decisions_router
from app.api.risks import router as risks_router
from app.api.reports import router as reports_router
from app.api.roles import router as roles_router
from app.api.users import router as users_router

__all__ = [
    "audit_logs_router",
    "committees_router",
    "committee_members_router",
    "health_router",
    "risk_actions_router",
    "risk_assessments_router",
    "risk_decisions_router",
    "risks_router",
    "reports_router",
    "roles_router",
    "users_router",
]
