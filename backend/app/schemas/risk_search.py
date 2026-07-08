import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus


ALLOWED_RISK_LIST_SORT_FIELDS = {
    "risk_id",
    "created_at",
    "updated_at",
    "domain",
    "workflow_status",
    "lifecycle_status",
}
ALLOWED_RISK_LIST_SORT_DIRECTIONS = {"asc", "desc"}


class RiskRecordListFilters(BaseModel):
    search: str | None = None
    risk_id: str | None = None
    domain: RiskDomain | None = None
    board_of_origin_id: uuid.UUID | None = None
    workflow_status: RiskWorkflowStatus | None = None
    lifecycle_status: RiskLifecycleStatus | None = None
    owner_user_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID | None = None
    latest_risk_level: str | None = None
    has_overdue_actions: bool | None = None
    has_due_or_overdue_monitoring: bool | None = None
    include_archived: bool = False
    sort_by: str = "updated_at"
    sort_direction: str = "desc"

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "search",
        "risk_id",
        "latest_risk_level",
        "sort_by",
        "sort_direction",
        mode="before",
    )
    @classmethod
    def _trim_blank_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator("sort_by")
    @classmethod
    def _validate_sort_by(cls, value: str | None) -> str:
        sort_by = value or "updated_at"
        if sort_by not in ALLOWED_RISK_LIST_SORT_FIELDS:
            raise ValueError(f"Unsupported sort_by value: {sort_by}")
        return sort_by

    @field_validator("sort_direction")
    @classmethod
    def _validate_sort_direction(cls, value: str | None) -> str:
        sort_direction = (value or "desc").lower()
        if sort_direction not in ALLOWED_RISK_LIST_SORT_DIRECTIONS:
            raise ValueError(f"Unsupported sort_direction value: {sort_direction}")
        return sort_direction
