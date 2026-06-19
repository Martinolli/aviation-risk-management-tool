from fastapi import FastAPI

from app.api.audit_logs import router as audit_log_router
from app.api.committees import router as committee_router
from app.api.health import router as health_router
from app.api.risk_actions import router as risk_action_router
from app.api.risk_assessments import router as risk_assessment_router
from app.api.risk_decisions import router as risk_decision_router
from app.api.risks import router as risk_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(audit_log_router)
    app.include_router(committee_router)
    app.include_router(risk_router)
    app.include_router(risk_assessment_router)
    app.include_router(risk_action_router)
    app.include_router(risk_decision_router)
    return app


app = create_app()
