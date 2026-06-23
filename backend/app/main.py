import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
from app.core.errors import (
    ErrorCode,
    error_from_http_exception,
    error_response,
    validation_error_details,
)


logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code, message, details = error_from_http_exception(exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, message, details),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                ErrorCode.VALIDATION_ERROR,
                "Request validation failed.",
                validation_error_details(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled API exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_response(
                ErrorCode.INTERNAL_SERVER_ERROR,
                "An unexpected error occurred.",
            ),
        )


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
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
