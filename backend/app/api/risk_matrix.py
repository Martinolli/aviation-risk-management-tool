import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.risk_matrix import (
    RiskLevelCreate, RiskLevelRead, RiskLevelUpdate,
    RiskLikelihoodLevelCreate, RiskLikelihoodLevelRead, RiskLikelihoodLevelUpdate,
    RiskMatrixArchive, RiskMatrixCellCreate, RiskMatrixCellRead, RiskMatrixCellUpdate,
    RiskSeverityLevelCreate, RiskSeverityLevelRead, RiskSeverityLevelUpdate,
)
from app.services.admin_authorization_service import AdminAuthorizationBusinessRuleError
from app.services.risk_matrix_service import (
    RiskMatrixBusinessRuleError, RiskMatrixNotFoundError,
    archive_likelihood_level, archive_matrix_cell, archive_risk_level, archive_severity_level,
    create_likelihood_level, create_matrix_cell, create_risk_level, create_severity_level,
    get_likelihood_level, get_matrix_cell, get_risk_level, get_severity_level,
    list_likelihood_levels, list_matrix_cells, list_risk_levels, list_severity_levels,
    update_likelihood_level, update_matrix_cell, update_risk_level, update_severity_level,
)

router = APIRouter(prefix="/risk-matrix", tags=["risk-matrix"])


def _require_user(current_user: User | None) -> User:
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user


def _write(db: Session, operation: Callable[[], Any]) -> Any:
    try:
        record = operation()
        db.commit()
        db.refresh(record)
        return record
    except RiskMatrixNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (AdminAuthorizationBusinessRuleError, RiskMatrixBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_or_404(record: Any) -> Any:
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk matrix record not found")
    return record


@router.post("/severity-levels", response_model=RiskSeverityLevelRead, status_code=status.HTTP_201_CREATED)
def create_severity_endpoint(data: RiskSeverityLevelCreate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: create_severity_level(db, data=data, changed_by_user_id=user.id))


@router.get("/severity-levels", response_model=list[RiskSeverityLevelRead])
def list_severity_endpoint(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return list_severity_levels(db, include_inactive=include_inactive)


@router.get("/severity-levels/{severity_level_id}", response_model=RiskSeverityLevelRead)
def get_severity_endpoint(severity_level_id: uuid.UUID, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return _get_or_404(get_severity_level(db, severity_level_id=severity_level_id))


@router.patch("/severity-levels/{severity_level_id}", response_model=RiskSeverityLevelRead)
def update_severity_endpoint(severity_level_id: uuid.UUID, data: RiskSeverityLevelUpdate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: update_severity_level(db, severity_level_id=severity_level_id, data=data, changed_by_user_id=user.id))


@router.post("/severity-levels/{severity_level_id}/archive", response_model=RiskSeverityLevelRead)
def archive_severity_endpoint(severity_level_id: uuid.UUID, data: RiskMatrixArchive | None = None, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: archive_severity_level(db, severity_level_id=severity_level_id, changed_by_user_id=user.id, reason=data.reason if data else None))


@router.post("/likelihood-levels", response_model=RiskLikelihoodLevelRead, status_code=status.HTTP_201_CREATED)
def create_likelihood_endpoint(data: RiskLikelihoodLevelCreate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: create_likelihood_level(db, data=data, changed_by_user_id=user.id))


@router.get("/likelihood-levels", response_model=list[RiskLikelihoodLevelRead])
def list_likelihood_endpoint(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return list_likelihood_levels(db, include_inactive=include_inactive)


@router.get("/likelihood-levels/{likelihood_level_id}", response_model=RiskLikelihoodLevelRead)
def get_likelihood_endpoint(likelihood_level_id: uuid.UUID, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return _get_or_404(get_likelihood_level(db, likelihood_level_id=likelihood_level_id))


@router.patch("/likelihood-levels/{likelihood_level_id}", response_model=RiskLikelihoodLevelRead)
def update_likelihood_endpoint(likelihood_level_id: uuid.UUID, data: RiskLikelihoodLevelUpdate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: update_likelihood_level(db, likelihood_level_id=likelihood_level_id, data=data, changed_by_user_id=user.id))


@router.post("/likelihood-levels/{likelihood_level_id}/archive", response_model=RiskLikelihoodLevelRead)
def archive_likelihood_endpoint(likelihood_level_id: uuid.UUID, data: RiskMatrixArchive | None = None, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: archive_likelihood_level(db, likelihood_level_id=likelihood_level_id, changed_by_user_id=user.id, reason=data.reason if data else None))


@router.post("/risk-levels", response_model=RiskLevelRead, status_code=status.HTTP_201_CREATED)
def create_risk_level_endpoint(data: RiskLevelCreate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: create_risk_level(db, data=data, changed_by_user_id=user.id))


@router.get("/risk-levels", response_model=list[RiskLevelRead])
def list_risk_level_endpoint(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return list_risk_levels(db, include_inactive=include_inactive)


@router.get("/risk-levels/{risk_level_id}", response_model=RiskLevelRead)
def get_risk_level_endpoint(risk_level_id: uuid.UUID, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return _get_or_404(get_risk_level(db, risk_level_id=risk_level_id))


@router.patch("/risk-levels/{risk_level_id}", response_model=RiskLevelRead)
def update_risk_level_endpoint(risk_level_id: uuid.UUID, data: RiskLevelUpdate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: update_risk_level(db, risk_level_id=risk_level_id, data=data, changed_by_user_id=user.id))


@router.post("/risk-levels/{risk_level_id}/archive", response_model=RiskLevelRead)
def archive_risk_level_endpoint(risk_level_id: uuid.UUID, data: RiskMatrixArchive | None = None, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: archive_risk_level(db, risk_level_id=risk_level_id, changed_by_user_id=user.id, reason=data.reason if data else None))


@router.post("/cells", response_model=RiskMatrixCellRead, status_code=status.HTTP_201_CREATED)
def create_cell_endpoint(data: RiskMatrixCellCreate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: create_matrix_cell(db, data=data, changed_by_user_id=user.id))


@router.get("/cells", response_model=list[RiskMatrixCellRead])
def list_cells_endpoint(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return list_matrix_cells(db, include_inactive=include_inactive)


@router.get("/cells/{matrix_cell_id}", response_model=RiskMatrixCellRead)
def get_cell_endpoint(matrix_cell_id: uuid.UUID, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    _require_user(current_user)
    return _get_or_404(get_matrix_cell(db, matrix_cell_id=matrix_cell_id))


@router.patch("/cells/{matrix_cell_id}", response_model=RiskMatrixCellRead)
def update_cell_endpoint(matrix_cell_id: uuid.UUID, data: RiskMatrixCellUpdate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: update_matrix_cell(db, matrix_cell_id=matrix_cell_id, data=data, changed_by_user_id=user.id))


@router.post("/cells/{matrix_cell_id}/archive", response_model=RiskMatrixCellRead)
def archive_cell_endpoint(matrix_cell_id: uuid.UUID, data: RiskMatrixArchive | None = None, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    user = _require_user(current_user)
    return _write(db, lambda: archive_matrix_cell(db, matrix_cell_id=matrix_cell_id, changed_by_user_id=user.id, reason=data.reason if data else None))
