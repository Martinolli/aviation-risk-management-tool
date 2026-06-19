from fastapi import FastAPI

from app.api.committees import router as committee_router
from app.api.health import router as health_router
from app.api.risks import router as risk_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(committee_router)
    app.include_router(risk_router)
    return app


app = create_app()
