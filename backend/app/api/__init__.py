from app.api.committees import router as committees_router
from app.api.health import router as health_router
from app.api.risk_actions import router as risk_actions_router
from app.api.risk_assessments import router as risk_assessments_router
from app.api.risk_decisions import router as risk_decisions_router
from app.api.risks import router as risks_router

__all__ = [
    "committees_router",
    "health_router",
    "risk_actions_router",
    "risk_assessments_router",
    "risk_decisions_router",
    "risks_router",
]
