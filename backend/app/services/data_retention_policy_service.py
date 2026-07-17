from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RetentionPolicyItem:
    record_type: str
    description: str
    default_retention_period: str
    archive_rule: str
    deletion_rule: str
    owner: str
    notes: str


@dataclass(frozen=True)
class RetentionPolicyRead:
    policy_name: str
    policy_version: str
    effective_status: str
    generated_at: datetime
    summary: str
    principles: list[str]
    items: list[RetentionPolicyItem]
    no_hard_delete_record_types: list[str]
    requires_legal_or_investigation_hold_review: list[str]


POLICY_NAME = "Data Retention and Archive Policy"
POLICY_VERSION = "0.1-mvp"
EFFECTIVE_STATUS = "Draft for SMS governance review"

PRINCIPLES = [
    "No Hard Delete: SMS governance records must be preserved.",
    "Audit Integrity: audit logs must not be manually edited or deleted.",
    "Closed risks should be archived, not hard-deleted.",
    "Evidence Preservation: evidence must remain traceable to the risk record.",
    (
        "Generated reports and exports support audit preparation and should be "
        "retained according to company policy."
    ),
    "Backup retention must be approved by company IT/security.",
    (
        "Legal / Investigation Hold: legal, investigation, airworthiness, or "
        "regulatory holds override normal retention periods."
    ),
    "Production retention rules require company approval.",
]

POLICY_ITEMS = [
    RetentionPolicyItem(
        record_type="Risk Records",
        description="Primary SMS governance risk records and lifecycle state.",
        default_retention_period=(
            "Minimum 10 years or company SMS/airworthiness requirement, "
            "whichever is longer."
        ),
        archive_rule="Closed risks may be archived after management review.",
        deletion_rule="No hard delete in MVP.",
        owner="SMS / risk management owner",
        notes="Archive Review should confirm closure, actions, monitoring, and holds.",
    ),
    RetentionPolicyItem(
        record_type="Risk Assessments",
        description="Initial, residual, and linked risk matrix assessments.",
        default_retention_period="Same as parent risk record.",
        archive_rule="Inherited from risk record.",
        deletion_rule="No hard delete.",
        owner="SMS / risk management owner",
        notes="Supports historical risk evaluation and decision traceability.",
    ),
    RetentionPolicyItem(
        record_type="Risk Decisions",
        description="Committee, management, acceptance, escalation, and closure decisions.",
        default_retention_period="Same as parent risk record.",
        archive_rule="Inherited from risk record.",
        deletion_rule="No hard delete.",
        owner="Decision authority / committee owner",
        notes="Decision records are governed SMS records.",
    ),
    RetentionPolicyItem(
        record_type="Mitigation Actions",
        description="Controls, mitigation action assignments, completion, and closure notes.",
        default_retention_period="Same as parent risk record.",
        archive_rule="Inherited from risk record.",
        deletion_rule="No hard delete.",
        owner="Action owner / SMS owner",
        notes="Actions must remain traceable to the risk they mitigate.",
    ),
    RetentionPolicyItem(
        record_type="Monitoring Reviews",
        description="Risk monitoring reviews, outcomes, effectiveness checks, and closure.",
        default_retention_period="Same as parent risk record.",
        archive_rule="Closed/cancelled reviews remain linked to parent risk.",
        deletion_rule="No hard delete.",
        owner="Monitoring owner / SMS owner",
        notes="Retain evidence of ongoing risk control effectiveness.",
    ),
    RetentionPolicyItem(
        record_type="Evidence Uploads",
        description="Uploaded evidence files and metadata attached to risk records.",
        default_retention_period=(
            "Same as parent risk record or investigation/legal hold requirement."
        ),
        archive_rule="Evidence may be archived from active view but remains stored.",
        deletion_rule="No hard delete in MVP.",
        owner="Evidence owner / SMS owner",
        notes="Evidence Preservation requires traceability to the risk record.",
    ),
    RetentionPolicyItem(
        record_type="Generated Reports",
        description="Generated DOCX reports, committee packs, minutes, and evidence packages.",
        default_retention_period=(
            "Minimum 10 years or according to SMS audit/committee record policy."
        ),
        archive_rule="May be moved to controlled archive storage.",
        deletion_rule="No hard delete without approved records disposition process.",
        owner="SMS / quality records owner",
        notes="Reports used for official review become controlled records.",
    ),
    RetentionPolicyItem(
        record_type="Audit Logs",
        description="System audit trail for governed actions and workflow changes.",
        default_retention_period="Permanent or as required by company SMS governance.",
        archive_rule="May be moved to long-term immutable archive.",
        deletion_rule="No manual deletion.",
        owner="SMS governance / cybersecurity owner",
        notes="Audit Integrity must be preserved for operational traceability.",
    ),
    RetentionPolicyItem(
        record_type="Committee Meetings and Minutes",
        description="Committee meeting records, agenda items, decisions, and minutes.",
        default_retention_period="Minimum 10 years or company governance requirement.",
        archive_rule="Finalized meetings remain retained.",
        deletion_rule="No hard delete.",
        owner="Committee secretary / governance owner",
        notes="Committee records support governance and audit preparation.",
    ),
    RetentionPolicyItem(
        record_type="User and Role Records",
        description="User, role, and committee membership records linked to governed records.",
        default_retention_period="Retain while associated records exist.",
        archive_rule="Deactivate users instead of deletion.",
        deletion_rule="No hard delete when linked to governance records.",
        owner="System administrator / cybersecurity owner",
        notes="Identity references must remain understandable for audit review.",
    ),
    RetentionPolicyItem(
        record_type="Backups",
        description="Operational recovery copies of database, evidence, and generated reports.",
        default_retention_period="Defined by company IT/security.",
        archive_rule="Rotate according to approved backup retention schedule.",
        deletion_rule="Deletion only according to approved backup retention policy.",
        owner="Company IT/security",
        notes="Backups do not replace formal SMS records retention.",
    ),
    RetentionPolicyItem(
        record_type="Exports",
        description="Risk registers, audit exports, evidence packages, and review extracts.",
        default_retention_period=(
            "Treat exported files as controlled records if used for committee, "
            "audit, or management review."
        ),
        archive_rule="Store in approved location.",
        deletion_rule="Follow company records policy.",
        owner="Exporting user / records owner",
        notes="Exports may contain sensitive SMS governance and evidence data.",
    ),
]

NO_HARD_DELETE_RECORD_TYPES = [
    "Risk Records",
    "Risk Assessments",
    "Risk Decisions",
    "Mitigation Actions",
    "Monitoring Reviews",
    "Evidence Uploads",
    "Generated Reports",
    "Audit Logs",
    "Committee Meetings and Minutes",
    "User and Role Records",
]

REQUIRES_LEGAL_OR_INVESTIGATION_HOLD_REVIEW = [
    "Risk Records",
    "Risk Assessments",
    "Risk Decisions",
    "Mitigation Actions",
    "Monitoring Reviews",
    "Evidence Uploads",
    "Generated Reports",
    "Audit Logs",
    "Committee Meetings and Minutes",
    "Exports",
]


def get_data_retention_policy() -> RetentionPolicyRead:
    return RetentionPolicyRead(
        policy_name=POLICY_NAME,
        policy_version=POLICY_VERSION,
        effective_status=EFFECTIVE_STATUS,
        generated_at=datetime.now(timezone.utc),
        summary=(
            "Draft MVP Data Retention and Archive Policy for SMS governance, "
            "No Hard Delete guardrails, Audit Integrity, Evidence Preservation, "
            "Archive Review, Retention Period guidance, and Legal / Investigation "
            "Hold awareness."
        ),
        principles=PRINCIPLES,
        items=POLICY_ITEMS,
        no_hard_delete_record_types=NO_HARD_DELETE_RECORD_TYPES,
        requires_legal_or_investigation_hold_review=(
            REQUIRES_LEGAL_OR_INVESTIGATION_HOLD_REVIEW
        ),
    )
