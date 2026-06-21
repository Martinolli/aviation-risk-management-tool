import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.risk_matrix import (
    RiskLevel,
    RiskLikelihoodLevel,
    RiskMatrixCell,
    RiskSeverityLevel,
)
from app.schemas.risk_matrix import (
    RiskLevelCreate,
    RiskLevelUpdate,
    RiskLikelihoodLevelCreate,
    RiskLikelihoodLevelUpdate,
    RiskMatrixCellCreate,
    RiskMatrixCellUpdate,
    RiskSeverityLevelCreate,
    RiskSeverityLevelUpdate,
)
from app.services.admin_authorization_service import validate_admin_actor

SEVERITY_ENTITY_TYPE = "RiskSeverityLevel"
LIKELIHOOD_ENTITY_TYPE = "RiskLikelihoodLevel"
RISK_LEVEL_ENTITY_TYPE = "RiskLevel"
CELL_ENTITY_TYPE = "RiskMatrixCell"


class RiskMatrixBusinessRuleError(ValueError):
    pass


class RiskMatrixNotFoundError(ValueError):
    pass


def _normalize_required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RiskMatrixBusinessRuleError(f"{field_name} must not be blank")
    return normalized


def _validate_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise RiskMatrixBusinessRuleError(f"{field_name} must be a positive integer")


def _snapshot(model: Any) -> dict[str, object]:
    return {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns
        if column.name not in {"archived_by_user_id"}
    }


def _create_reference(
    db: Session,
    *,
    model: type[RiskSeverityLevel] | type[RiskLikelihoodLevel] | type[RiskLevel],
    data: Any,
    changed_by_user_id: uuid.UUID | None,
    entity_type: str,
) -> Any:
    validate_admin_actor(db, user_id=changed_by_user_id)
    code = _normalize_required(data.code, "code").upper()
    name = _normalize_required(data.name, "name")
    _validate_positive(data.numeric_value, "numeric_value")
    if db.scalar(select(model).where(model.code == code)) is not None:
        raise RiskMatrixBusinessRuleError("A risk matrix code with this value already exists")
    values = data.model_dump()
    values.update(code=code, name=name)
    reference = model(**values)
    db.add(reference)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=entity_type,
        entity_id=reference.id,
        created_by_user_id=changed_by_user_id,
        new_value=_snapshot(reference),
    )
    return reference


def _list_reference(db: Session, *, model: Any, include_inactive: bool) -> list[Any]:
    statement = select(model).order_by(model.numeric_value)
    if not include_inactive:
        statement = statement.where(model.is_active.is_(True))
    return list(db.scalars(statement).all())


def _get_reference(db: Session, *, model: Any, record_id: uuid.UUID) -> Any | None:
    return db.get(model, record_id)


def _update_reference(
    db: Session,
    *,
    model: Any,
    record_id: uuid.UUID,
    data: Any,
    changed_by_user_id: uuid.UUID | None,
    entity_type: str,
    reason: str | None,
) -> Any:
    validate_admin_actor(db, user_id=changed_by_user_id)
    reference = db.get(model, record_id)
    if reference is None:
        raise RiskMatrixNotFoundError("Risk matrix record not found")
    update_data = data.model_dump(exclude_unset=True)
    if "code" in update_data:
        code = _normalize_required(update_data["code"], "code").upper()
        duplicate = db.scalar(
            select(model).where(model.code == code, model.id != reference.id)
        )
        if duplicate is not None:
            raise RiskMatrixBusinessRuleError("A risk matrix code with this value already exists")
        update_data["code"] = code
    if "name" in update_data:
        update_data["name"] = _normalize_required(update_data["name"], "name")
    if "numeric_value" in update_data:
        _validate_positive(update_data["numeric_value"], "numeric_value")
    for field_name, new_value in update_data.items():
        old_value = getattr(reference, field_name)
        if old_value == new_value:
            continue
        setattr(reference, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=entity_type,
            entity_id=reference.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )
    db.add(reference)
    db.flush()
    return reference


def _archive_reference(
    db: Session,
    *,
    model: Any,
    record_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    entity_type: str,
    reason: str | None,
) -> Any:
    validate_admin_actor(db, user_id=changed_by_user_id)
    reference = db.get(model, record_id)
    if reference is None:
        raise RiskMatrixNotFoundError("Risk matrix record not found")
    if not reference.is_active:
        raise RiskMatrixBusinessRuleError("Risk matrix record is already archived")
    old_value = _snapshot(reference)
    reference.is_active = False
    reference.archived_at = datetime.now(timezone.utc)
    reference.archived_by_user_id = changed_by_user_id
    db.add(reference)
    db.flush()
    audit_service.log_archive_action(
        db,
        entity_type=entity_type,
        entity_id=reference.id,
        changed_by_user_id=changed_by_user_id,
        old_value=old_value,
        new_value=_snapshot(reference),
        reason=reason,
    )
    return reference


def create_severity_level(db: Session, *, data: RiskSeverityLevelCreate, changed_by_user_id: uuid.UUID | None) -> RiskSeverityLevel:
    return _create_reference(db, model=RiskSeverityLevel, data=data, changed_by_user_id=changed_by_user_id, entity_type=SEVERITY_ENTITY_TYPE)


def list_severity_levels(db: Session, *, include_inactive: bool = False) -> list[RiskSeverityLevel]:
    return _list_reference(db, model=RiskSeverityLevel, include_inactive=include_inactive)


def get_severity_level(db: Session, *, severity_level_id: uuid.UUID) -> RiskSeverityLevel | None:
    return _get_reference(db, model=RiskSeverityLevel, record_id=severity_level_id)


def update_severity_level(db: Session, *, severity_level_id: uuid.UUID, data: RiskSeverityLevelUpdate, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskSeverityLevel:
    return _update_reference(db, model=RiskSeverityLevel, record_id=severity_level_id, data=data, changed_by_user_id=changed_by_user_id, entity_type=SEVERITY_ENTITY_TYPE, reason=reason)


def archive_severity_level(db: Session, *, severity_level_id: uuid.UUID, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskSeverityLevel:
    return _archive_reference(db, model=RiskSeverityLevel, record_id=severity_level_id, changed_by_user_id=changed_by_user_id, entity_type=SEVERITY_ENTITY_TYPE, reason=reason)


def create_likelihood_level(db: Session, *, data: RiskLikelihoodLevelCreate, changed_by_user_id: uuid.UUID | None) -> RiskLikelihoodLevel:
    return _create_reference(db, model=RiskLikelihoodLevel, data=data, changed_by_user_id=changed_by_user_id, entity_type=LIKELIHOOD_ENTITY_TYPE)


def list_likelihood_levels(db: Session, *, include_inactive: bool = False) -> list[RiskLikelihoodLevel]:
    return _list_reference(db, model=RiskLikelihoodLevel, include_inactive=include_inactive)


def get_likelihood_level(db: Session, *, likelihood_level_id: uuid.UUID) -> RiskLikelihoodLevel | None:
    return _get_reference(db, model=RiskLikelihoodLevel, record_id=likelihood_level_id)


def update_likelihood_level(db: Session, *, likelihood_level_id: uuid.UUID, data: RiskLikelihoodLevelUpdate, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskLikelihoodLevel:
    return _update_reference(db, model=RiskLikelihoodLevel, record_id=likelihood_level_id, data=data, changed_by_user_id=changed_by_user_id, entity_type=LIKELIHOOD_ENTITY_TYPE, reason=reason)


def archive_likelihood_level(db: Session, *, likelihood_level_id: uuid.UUID, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskLikelihoodLevel:
    return _archive_reference(db, model=RiskLikelihoodLevel, record_id=likelihood_level_id, changed_by_user_id=changed_by_user_id, entity_type=LIKELIHOOD_ENTITY_TYPE, reason=reason)


def create_risk_level(db: Session, *, data: RiskLevelCreate, changed_by_user_id: uuid.UUID | None) -> RiskLevel:
    return _create_reference(db, model=RiskLevel, data=data, changed_by_user_id=changed_by_user_id, entity_type=RISK_LEVEL_ENTITY_TYPE)


def list_risk_levels(db: Session, *, include_inactive: bool = False) -> list[RiskLevel]:
    return _list_reference(db, model=RiskLevel, include_inactive=include_inactive)


def get_risk_level(db: Session, *, risk_level_id: uuid.UUID) -> RiskLevel | None:
    return _get_reference(db, model=RiskLevel, record_id=risk_level_id)


def update_risk_level(db: Session, *, risk_level_id: uuid.UUID, data: RiskLevelUpdate, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskLevel:
    return _update_reference(db, model=RiskLevel, record_id=risk_level_id, data=data, changed_by_user_id=changed_by_user_id, entity_type=RISK_LEVEL_ENTITY_TYPE, reason=reason)


def archive_risk_level(db: Session, *, risk_level_id: uuid.UUID, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskLevel:
    return _archive_reference(db, model=RiskLevel, record_id=risk_level_id, changed_by_user_id=changed_by_user_id, entity_type=RISK_LEVEL_ENTITY_TYPE, reason=reason)


def _active_reference(db: Session, model: Any, record_id: uuid.UUID, name: str) -> Any:
    record = db.get(model, record_id)
    if record is None or not record.is_active:
        raise RiskMatrixBusinessRuleError(f"{name} does not exist or is inactive")
    return record


def create_matrix_cell(db: Session, *, data: RiskMatrixCellCreate, changed_by_user_id: uuid.UUID | None) -> RiskMatrixCell:
    validate_admin_actor(db, user_id=changed_by_user_id)
    severity = _active_reference(db, RiskSeverityLevel, data.severity_level_id, "Severity level")
    likelihood = _active_reference(db, RiskLikelihoodLevel, data.likelihood_level_id, "Likelihood level")
    _active_reference(db, RiskLevel, data.risk_level_id, "Risk level")
    if db.scalar(select(RiskMatrixCell).where(RiskMatrixCell.severity_level_id == severity.id, RiskMatrixCell.likelihood_level_id == likelihood.id)) is not None:
        raise RiskMatrixBusinessRuleError("A matrix cell already exists for this severity and likelihood pair")
    if data.score is not None:
        _validate_positive(data.score, "score")
    cell = RiskMatrixCell(
        severity_level_id=severity.id,
        likelihood_level_id=likelihood.id,
        risk_level_id=data.risk_level_id,
        score=data.score if data.score is not None else severity.numeric_value * likelihood.numeric_value,
        label=data.label.strip() if data.label else None,
        is_active=True,
    )
    db.add(cell)
    db.flush()
    audit_service.log_entity_created(db, entity_type=CELL_ENTITY_TYPE, entity_id=cell.id, created_by_user_id=changed_by_user_id, new_value=_snapshot(cell))
    return cell


def list_matrix_cells(db: Session, *, include_inactive: bool = False) -> list[RiskMatrixCell]:
    statement = select(RiskMatrixCell).order_by(RiskMatrixCell.created_at)
    if not include_inactive:
        statement = statement.where(RiskMatrixCell.is_active.is_(True))
    return list(db.scalars(statement).all())


def get_matrix_cell(db: Session, *, matrix_cell_id: uuid.UUID) -> RiskMatrixCell | None:
    return db.get(RiskMatrixCell, matrix_cell_id)


def update_matrix_cell(db: Session, *, matrix_cell_id: uuid.UUID, data: RiskMatrixCellUpdate, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskMatrixCell:
    validate_admin_actor(db, user_id=changed_by_user_id)
    cell = db.get(RiskMatrixCell, matrix_cell_id)
    if cell is None:
        raise RiskMatrixNotFoundError("Risk matrix cell not found")
    update_data = data.model_dump(exclude_unset=True)
    if "risk_level_id" in update_data and update_data["risk_level_id"] is not None:
        _active_reference(db, RiskLevel, update_data["risk_level_id"], "Risk level")
    if "score" in update_data and update_data["score"] is not None:
        _validate_positive(update_data["score"], "score")
    if "label" in update_data and update_data["label"] is not None:
        update_data["label"] = update_data["label"].strip() or None
    for field_name, new_value in update_data.items():
        if new_value is None and field_name == "score":
            continue
        old_value = getattr(cell, field_name)
        if old_value == new_value:
            continue
        setattr(cell, field_name, new_value)
        audit_service.log_change(db, entity_type=CELL_ENTITY_TYPE, entity_id=cell.id, field_name=field_name, old_value=old_value, new_value=new_value, changed_by_user_id=changed_by_user_id, reason=reason)
    db.add(cell)
    db.flush()
    return cell


def archive_matrix_cell(db: Session, *, matrix_cell_id: uuid.UUID, changed_by_user_id: uuid.UUID | None, reason: str | None = None) -> RiskMatrixCell:
    return _archive_reference(db, model=RiskMatrixCell, record_id=matrix_cell_id, changed_by_user_id=changed_by_user_id, entity_type=CELL_ENTITY_TYPE, reason=reason)
