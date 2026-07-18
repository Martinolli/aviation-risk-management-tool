from fastapi import APIRouter

from app.core.config import settings
from app.core.version import APP_RELEASE_NAME, APP_RELEASE_STATUS, APP_VERSION

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "aviation-risk-management-tool"}


@router.get("/health/readiness")
def readiness_check() -> dict[str, object]:
    return {
        "status": "ready",
        "app_name": settings.app_name,
        "app_version": APP_VERSION,
        "release_name": APP_RELEASE_NAME,
        "release_status": APP_RELEASE_STATUS,
        "environment": settings.environment,
        "database_configured": bool(settings.database_url.strip()),
        "cors_origins_count": len(settings.cors_origins_list),
        "evidence_storage_configured": bool(settings.evidence_storage_dir.strip()),
        "generated_reports_configured": bool(settings.generated_reports_dir.strip()),
        "auth_fallback_enabled": settings.enable_x_user_id_auth_fallback,
        "production_safety_enforced": (
            settings.is_production and settings.require_secure_production_settings
        ),
        "logging_configured": True,
        "log_level": settings.normalized_log_level,
        "log_format": settings.log_format,
        "request_logging_enabled": settings.enable_request_logging,
        "request_id_header": settings.request_id_header,
    }
