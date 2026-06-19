import re
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocumentObject
from sqlalchemy.orm import Session

from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.services.risk_detail_service import (
    RiskDetailNotFoundError,
    get_risk_record_detail,
)


class ReportGenerationError(ValueError):
    pass


class ReportRiskNotFoundError(ReportGenerationError):
    pass


def _format_enum(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _safe_text(value)


def _safe_text(value: Any) -> str:
    if value is None:
        return "Not recorded."
    if isinstance(value, Enum):
        return _format_enum(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    text = str(value)
    return text if text else "Not recorded."


def _add_key_value_paragraph(
    document: DocumentObject,
    key: str,
    value: Any,
) -> None:
    paragraph = document.add_paragraph()
    paragraph.add_run(f"{key}: ").bold = True
    paragraph.add_run(_safe_text(value))


def _add_bullet_list(document: DocumentObject, items: list[str] | None) -> None:
    if not items:
        document.add_paragraph("Not recorded.")
        return

    for item in items:
        document.add_paragraph(_safe_text(item), style="List Bullet")


def _add_table(
    document: DocumentObject,
    headers: list[str],
    rows: list[list[Any]],
) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    header_cells = table.rows[0].cells
    for index, header in enumerate(headers):
        header_cells[index].text = header

    for row in rows:
        row_cells = table.add_row().cells
        for index, value in enumerate(row):
            row_cells[index].text = _safe_text(value)


def _safe_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    filename = filename.strip("._")
    return filename or "risk_dossier"


def _assessment_rows(assessments: list[RiskAssessment]) -> list[list[Any]]:
    return [
        [
            assessment.assessment_type,
            assessment.severity,
            assessment.likelihood,
            assessment.risk_level,
            assessment.rationale,
            _format_datetime(assessment.assessed_at),
        ]
        for assessment in assessments
    ]


def _action_rows(actions: list[RiskAction]) -> list[list[Any]]:
    return [
        [
            action.title,
            action.status,
            action.action_owner_user_id,
            _format_datetime(action.due_date),
            _format_datetime(action.completed_at),
            action.completion_notes,
        ]
        for action in actions
    ]


def _decision_rows(decisions: list[RiskDecision]) -> list[list[Any]]:
    return [
        [
            decision.decision_type,
            decision.committee_id,
            decision.decision_text,
            decision.decided_by_user_id,
            _format_datetime(decision.decided_at),
        ]
        for decision in decisions
    ]


def generate_risk_dossier_docx(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    output_dir: Path | str,
) -> Path:
    try:
        detail = get_risk_record_detail(db, risk_record_id=risk_record_id)
    except RiskDetailNotFoundError as exc:
        raise ReportRiskNotFoundError("Risk record not found") from exc

    risk_record: RiskRecord = detail["risk_record"]
    assessments: list[RiskAssessment] = detail["assessments"]
    actions: list[RiskAction] = detail["actions"]
    decisions: list[RiskDecision] = detail["decisions"]
    audit_summary: dict[str, Any] = detail["audit_summary"]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    base_name = risk_record.risk_id or f"risk_{risk_record.id}"
    file_path = output_path / f"{_safe_filename(base_name)}_dossier.docx"

    document = Document()
    document.add_heading("Risk Dossier Report", 0)
    _add_key_value_paragraph(document, "Risk ID", risk_record.risk_id)
    _add_key_value_paragraph(document, "Internal UUID", risk_record.id)
    _add_key_value_paragraph(
        document,
        "Generated at UTC",
        datetime.now(timezone.utc).isoformat(),
    )

    document.add_heading("Section 1 - Risk Record Summary", level=1)
    _add_key_value_paragraph(
        document,
        "Problem Description",
        risk_record.problem_description,
    )
    _add_key_value_paragraph(document, "Source Trigger", risk_record.source_trigger)
    _add_key_value_paragraph(document, "Domain", risk_record.domain)
    _add_key_value_paragraph(document, "System Scope", risk_record.system_scope)
    _add_key_value_paragraph(document, "Central Event", risk_record.central_event)
    _add_key_value_paragraph(
        document,
        "Hazard Statement",
        risk_record.hazard_statement,
    )
    _add_key_value_paragraph(document, "Workflow Status", risk_record.workflow_status)
    _add_key_value_paragraph(document, "Lifecycle Status", risk_record.lifecycle_status)
    _add_key_value_paragraph(
        document,
        "Board of Origin ID",
        risk_record.board_of_origin_id,
    )
    _add_key_value_paragraph(document, "Owner User ID", risk_record.owner_user_id)
    _add_key_value_paragraph(document, "Created At", risk_record.created_at)
    _add_key_value_paragraph(document, "Updated At", risk_record.updated_at)

    document.add_heading(
        "Section 2 - Causes, Consequences, and Existing Controls",
        level=1,
    )
    document.add_heading("Causes", level=2)
    _add_bullet_list(document, risk_record.causes)
    document.add_heading("Consequences", level=2)
    _add_bullet_list(document, risk_record.consequences)
    document.add_heading("Existing Controls", level=2)
    _add_bullet_list(document, risk_record.existing_controls)

    document.add_heading("Section 3 - Risk Assessments", level=1)
    if assessments:
        _add_table(
            document,
            ["Type", "Severity", "Likelihood", "Risk Level", "Rationale", "Assessed At"],
            _assessment_rows(assessments),
        )
    else:
        document.add_paragraph("No risk assessments recorded.")

    document.add_heading("Section 4 - Mitigation / Risk Actions", level=1)
    if actions:
        _add_table(
            document,
            [
                "Title",
                "Status",
                "Owner User ID",
                "Due Date",
                "Completed At",
                "Completion Notes",
            ],
            _action_rows(actions),
        )
    else:
        document.add_paragraph("No risk actions recorded.")

    document.add_heading("Section 5 - Committee Decisions", level=1)
    if decisions:
        _add_table(
            document,
            ["Decision Type", "Committee ID", "Decision Text", "Decided By", "Decided At"],
            _decision_rows(decisions),
        )
    else:
        document.add_paragraph("No committee decisions recorded.")

    document.add_heading("Section 6 - Audit Summary", level=1)
    _add_key_value_paragraph(
        document,
        "Total Audit Records",
        audit_summary["total_count"],
    )
    _add_key_value_paragraph(document, "Create Records", audit_summary["create_count"])
    _add_key_value_paragraph(document, "Update Records", audit_summary["update_count"])
    _add_key_value_paragraph(
        document,
        "Workflow Records",
        audit_summary["workflow_count"],
    )
    _add_key_value_paragraph(
        document,
        "Latest Audit Change",
        audit_summary["latest_changed_at"],
    )

    document.add_heading("Section 7 - Notes", level=1)
    document.add_paragraph(
        "This report is generated from system records. It does not replace formal "
        "committee approval, accountable manager acceptance, or required regulatory "
        "documentation."
    )

    try:
        document.save(file_path)
    except Exception as exc:
        raise ReportGenerationError("Failed to generate risk dossier DOCX") from exc

    return file_path
