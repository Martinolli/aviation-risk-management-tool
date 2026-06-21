from fastapi import FastAPI

from app.api.audit_logs import router as audit_log_router
from app.api.auth import router as auth_router
from app.api.committees import router as committee_router
from app.api.committee_members import router as committee_member_router
from app.api.health import router as health_router
from app.api.risk_actions import router as risk_action_router
from app.api.risk_assessments import router as risk_assessment_router
from app.api.risk_decisions import router as risk_decision_router
from app.api.risk_matrix import router as risk_matrix_router
from app.api.risks import router as risk_router
from app.api.reports import router as report_router
from app.api.roles import router as role_router
from app.api.users import router as user_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(audit_log_router)
    app.include_router(committee_router)
    app.include_router(committee_member_router)
    app.include_router(risk_router)
    app.include_router(risk_assessment_router)
    app.include_router(risk_action_router)
    app.include_router(risk_decision_router)
    app.include_router(risk_matrix_router)
    app.include_router(report_router)
    app.include_router(role_router)
    app.include_router(user_router)
    return app


app = create_app()
