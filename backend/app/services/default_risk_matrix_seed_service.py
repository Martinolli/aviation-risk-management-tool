import uuid
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

DEFAULT_SEVERITY_LEVELS = [
    {"code": "S1", "name": "Negligible", "numeric_value": 1, "description": "No safety effect or negligible operational impact."},
    {"code": "S2", "name": "Minor", "numeric_value": 2, "description": "Minor injury, minor system degradation, or limited operational impact."},
    {"code": "S3", "name": "Major", "numeric_value": 3, "description": "Significant safety margin reduction, serious operational impact, or serious incident potential."},
    {"code": "S4", "name": "Hazardous", "numeric_value": 4, "description": "Large safety margin reduction, serious injury potential, or major aircraft/system impact."},
    {"code": "S5", "name": "Catastrophic", "numeric_value": 5, "description": "Accident-level consequence, fatal injury potential, or loss of aircraft."},
]

DEFAULT_LIKELIHOOD_LEVELS = [
    {"code": "L1", "name": "Extremely Improbable", "numeric_value": 1, "description": "Not expected to occur during the operational life of the system or fleet."},
    {"code": "L2", "name": "Remote", "numeric_value": 2, "description": "Unlikely, but possible during the operational life of the system or fleet."},
    {"code": "L3", "name": "Occasional", "numeric_value": 3, "description": "Could occur sometimes during operation or testing."},
    {"code": "L4", "name": "Probable", "numeric_value": 4, "description": "Expected to occur several times during operation or testing."},
    {"code": "L5", "name": "Frequent", "numeric_value": 5, "description": "Likely to occur often or repeatedly during operation or testing."},
]

DEFAULT_RISK_LEVELS = [
    {"code": "LOW", "name": "Low", "numeric_value": 1, "color": "green", "is_tolerable": True, "requires_mitigation": False, "requires_escalation": False, "description": "Acceptable with routine monitoring."},
    {"code": "MEDIUM", "name": "Medium", "numeric_value": 2, "color": "yellow", "is_tolerable": True, "requires_mitigation": True, "requires_escalation": False, "description": "Tolerable with mitigation or documented control."},
    {"code": "HIGH", "name": "High", "numeric_value": 3, "color": "orange", "is_tolerable": False, "requires_mitigation": True, "requires_escalation": True, "description": "Not normally acceptable without mitigation and management review."},
    {"code": "EXTREME", "name": "Extreme", "numeric_value": 4, "color": "red", "is_tolerable": False, "requires_mitigation": True, "requires_escalation": True, "description": "Unacceptable unless risk is reduced or formally accepted by appropriate authority."},
]


class DefaultRiskMatrixSeedError(ValueError):
    pass


def _risk_level_code_for_score(score: int) -> str:
    if score <= 3:
        return "LOW"
    if score <= 7:
        return "MEDIUM"
    if score <= 14:
        return "HIGH"
    return "EXTREME"


def _snapshot(record: Any) -> dict[str, object]:
    return {column.name: getattr(record, column.name) for column in record.__table__.columns}


def _upsert_reference(
    db: Session,
    *,
    model: Any,
    definition: dict[str, object],
    entity_type: str,
    changed_by_user_id: uuid.UUID | None,
    overwrite_existing: bool,
) -> tuple[Any, bool, bool]:
    record = db.scalar(select(model).where(model.code == definition["code"]))
    if record is None:
        record = model(**definition, is_active=True)
        db.add(record)
        db.flush()
        audit_service.log_entity_created(db, entity_type=entity_type, entity_id=record.id, created_by_user_id=changed_by_user_id, new_value=_snapshot(record))
        return record, True, False
    if not record.is_active:
        raise DefaultRiskMatrixSeedError(f"Inactive default {entity_type} code exists: {definition['code']}")
    if not overwrite_existing:
        return record, False, False
    updated = False
    for field_name, new_value in definition.items():
        old_value = getattr(record, field_name)
        if old_value == new_value:
            continue
        setattr(record, field_name, new_value)
        audit_service.log_change(db, entity_type=entity_type, entity_id=record.id, field_name=field_name, old_value=old_value, new_value=new_value, changed_by_user_id=changed_by_user_id)
        updated = True
    db.add(record)
    db.flush()
    return record, False, updated


def seed_default_risk_matrix(
    db: Session,
    *,
    changed_by_user_id: uuid.UUID | None = None,
    overwrite_existing: bool = False,
) -> dict[str, object]:
    severity_levels: list[RiskSeverityLevel] = []
    likelihood_levels: list[RiskLikelihoodLevel] = []
    risk_levels: list[RiskLevel] = []
    counts = {
        "created_severity_count": 0, "created_likelihood_count": 0,
        "created_risk_level_count": 0, "created_cell_count": 0,
        "updated_severity_count": 0, "updated_likelihood_count": 0,
        "updated_risk_level_count": 0, "updated_cell_count": 0,
    }
    for definition in DEFAULT_SEVERITY_LEVELS:
        record, created, updated = _upsert_reference(db, model=RiskSeverityLevel, definition=definition, entity_type="RiskSeverityLevel", changed_by_user_id=changed_by_user_id, overwrite_existing=overwrite_existing)
        severity_levels.append(record)
        counts["created_severity_count"] += int(created)
        counts["updated_severity_count"] += int(updated)
    for definition in DEFAULT_LIKELIHOOD_LEVELS:
        record, created, updated = _upsert_reference(db, model=RiskLikelihoodLevel, definition=definition, entity_type="RiskLikelihoodLevel", changed_by_user_id=changed_by_user_id, overwrite_existing=overwrite_existing)
        likelihood_levels.append(record)
        counts["created_likelihood_count"] += int(created)
        counts["updated_likelihood_count"] += int(updated)
    for definition in DEFAULT_RISK_LEVELS:
        record, created, updated = _upsert_reference(db, model=RiskLevel, definition=definition, entity_type="RiskLevel", changed_by_user_id=changed_by_user_id, overwrite_existing=overwrite_existing)
        risk_levels.append(record)
        counts["created_risk_level_count"] += int(created)
        counts["updated_risk_level_count"] += int(updated)

    risk_levels_by_code = {risk_level.code: risk_level for risk_level in risk_levels}
    matrix_cells: list[RiskMatrixCell] = []
    for severity in severity_levels:
        for likelihood in likelihood_levels:
            score = severity.numeric_value * likelihood.numeric_value
            values = {
                "risk_level_id": risk_levels_by_code[_risk_level_code_for_score(score)].id,
                "score": score,
                "label": f"{severity.code}-{likelihood.code}",
            }
            cell = db.scalar(select(RiskMatrixCell).where(RiskMatrixCell.severity_level_id == severity.id, RiskMatrixCell.likelihood_level_id == likelihood.id))
            if cell is None:
                cell = RiskMatrixCell(severity_level_id=severity.id, likelihood_level_id=likelihood.id, **values, is_active=True)
                db.add(cell)
                db.flush()
                audit_service.log_entity_created(db, entity_type="RiskMatrixCell", entity_id=cell.id, created_by_user_id=changed_by_user_id, new_value=_snapshot(cell))
                counts["created_cell_count"] += 1
            else:
                if not cell.is_active:
                    raise DefaultRiskMatrixSeedError(f"Inactive default RiskMatrixCell exists: {severity.code}-{likelihood.code}")
                if overwrite_existing:
                    updated = False
                    for field_name, new_value in values.items():
                        old_value = getattr(cell, field_name)
                        if old_value == new_value:
                            continue
                        setattr(cell, field_name, new_value)
                        audit_service.log_change(db, entity_type="RiskMatrixCell", entity_id=cell.id, field_name=field_name, old_value=old_value, new_value=new_value, changed_by_user_id=changed_by_user_id)
                        updated = True
                    if updated:
                        db.add(cell)
                        db.flush()
                        counts["updated_cell_count"] += 1
            matrix_cells.append(cell)
    return {
        **counts,
        "total_cells": len(matrix_cells),
        "severity_levels": severity_levels,
        "likelihood_levels": likelihood_levels,
        "risk_levels": risk_levels,
        "matrix_cells": matrix_cells,
    }
