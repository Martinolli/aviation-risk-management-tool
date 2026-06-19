import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk import RiskRecord

RISK_ID_PATTERN = re.compile(r"^RISK-(\d{4})-(\d{4})$")


class RiskNumberingError(ValueError):
    pass


def parse_risk_id(risk_id: str) -> tuple[int, int] | None:
    match = RISK_ID_PATTERN.fullmatch(risk_id)
    if match is None:
        return None

    year, sequence = match.groups()
    return int(year), int(sequence)


def generate_next_risk_id(
    db: Session,
    *,
    year: int | None = None,
) -> str:
    selected_year = year if year is not None else datetime.now(timezone.utc).year
    prefix = f"RISK-{selected_year}-"
    statement = select(RiskRecord.risk_id).where(RiskRecord.risk_id.like(f"{prefix}%"))

    highest_sequence = 0
    for risk_id in db.scalars(statement):
        if risk_id is None:
            continue

        parsed_risk_id = parse_risk_id(risk_id)
        if parsed_risk_id is None:
            continue

        parsed_year, sequence = parsed_risk_id
        if parsed_year == selected_year:
            highest_sequence = max(highest_sequence, sequence)

    # This MVP implementation is intentionally simple. Production numbering should
    # use a transaction lock, sequence table, advisory lock, or dedicated counter
    # table to prevent duplicate IDs under concurrent risk creation.
    return f"RISK-{selected_year}-{highest_sequence + 1:04d}"
