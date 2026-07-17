from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PermissionMatrixRule:
    area: str
    capability: str
    allowed_roles_or_users: list[str]
    authority_level: str | None
    access_basis: str
    restrictions: str
    audit_expected: bool
    notes: str | None = None


@dataclass(frozen=True)
class PermissionMatrixSection:
    section: str
    description: str
    rules: list[PermissionMatrixRule]


@dataclass(frozen=True)
class PermissionMatrix:
    policy_name: str
    policy_version: str
    effective_status: str
    generated_at: datetime
    summary: str
    principles: list[str]
    sections: list[PermissionMatrixSection]


POLICY_NAME = "Permission Matrix and Access Control Policy"
POLICY_VERSION = "0.1-mvp"
EFFECTIVE_STATUS = "Draft for SMS governance review"

PRINCIPLES = [
    "Access Control is based on authenticated active users.",
    "Users only see records they are authorized to read.",
    "Board of Origin controls LOW-level operational review visibility.",
    (
        "MIDDLE and HIGH Fixed Governance Committee members provide oversight "
        "visibility according to current system rules."
    ),
    "Governed records should be changed through workflows, not direct deletion.",
    "Exports must preserve the same authorization boundary as on-screen records.",
    "Audit-relevant actions must create audit log entries.",
    "Authority Level determines committee decision and escalation scope.",
    "Admin governance actions must remain restricted.",
    "Data retention, archive, restore, and audit integrity must be preserved.",
]


def _rule(
    area: str,
    capability: str,
    allowed: list[str],
    authority_level: str | None,
    access_basis: str,
    restrictions: str,
    audit_expected: bool,
    notes: str | None = None,
) -> PermissionMatrixRule:
    return PermissionMatrixRule(
        area=area,
        capability=capability,
        allowed_roles_or_users=allowed,
        authority_level=authority_level,
        access_basis=access_basis,
        restrictions=restrictions,
        audit_expected=audit_expected,
        notes=notes,
    )


SECTIONS = [
    PermissionMatrixSection(
        section="Authentication and Session",
        description="Session access for authenticated active users.",
        rules=[
            _rule(
                "Authentication and Session",
                "Login",
                ["Active users with valid credentials"],
                None,
                "JWT authentication after credential validation",
                "Inactive users denied.",
                False,
            ),
            _rule(
                "Authentication and Session",
                "Current User / Session Check",
                ["Authenticated active users"],
                None,
                "Bearer token current-user dependency",
                "Invalid, expired, or inactive sessions denied.",
                False,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Risk Record Access",
        description=(
            "Read, create, update, submit, archive, and restore expectations for "
            "governed SMS risk records."
        ),
        rules=[
            _rule(
                "Risk Record Access",
                "Create Risk Record",
                ["Authenticated active users"],
                "Usually LOW / Board of Origin assignment before submission",
                "Authenticated active user creates the initial governed record",
                "Board of Origin should be assigned before submission.",
                True,
            ),
            _rule(
                "Risk Record Access",
                "Read Risk Record",
                [
                    "creator",
                    "owner",
                    "Board of Origin active committee members",
                    "assigned assessor",
                    "assigned action owner",
                    "decision maker",
                    "committee members linked to decisions",
                    "fixed MIDDLE/HIGH governance members",
                ],
                "LOW / MIDDLE / HIGH",
                "Existing risk access service and related-record links",
                "Read access must not expose unauthorized records.",
                False,
                "Audit expected for export/report generation rather than ordinary read.",
            ),
            _rule(
                "Risk Record Access",
                "Update Draft Risk Record",
                ["creator", "owner", "authorized operational users before submission"],
                "LOW",
                "Existing update workflow and ownership checks",
                (
                    "Avoid editing closed/accepted governed records except through "
                    "controlled workflows."
                ),
                True,
            ),
            _rule(
                "Risk Record Access",
                "Submit Risk Record",
                ["creator", "owner", "authorized board member under existing rules"],
                "LOW / Board of Origin",
                "Existing submission workflow",
                "Submission follows the configured Board of Origin path.",
                True,
            ),
            _rule(
                "Risk Record Access",
                "Archive Risk Record",
                ["admin", "authorized governance role if implemented"],
                "LOW / MIDDLE / HIGH",
                "Archive Policy and governance authority",
                "No open Legal / Investigation Hold and no casual hard delete.",
                True,
            ),
            _rule(
                "Risk Record Access",
                "Restore Risk Record",
                ["admin", "authorized governance role if implemented"],
                "LOW / MIDDLE / HIGH",
                "Archive Policy and governance authority",
                "Restore must be justified and controlled.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Risk Assessment",
        description="Assessment access follows the readable parent risk record.",
        rules=[
            _rule(
                "Risk Assessment",
                "Create Initial Assessment",
                ["authorized users for readable risk records"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Risk must be accessible.",
                True,
            ),
            _rule(
                "Risk Assessment",
                "Create Residual Assessment",
                ["authorized users for readable risk records after mitigations"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record and mitigation workflow context",
                "Risk must be accessible.",
                True,
            ),
            _rule(
                "Risk Assessment",
                "Read Assessments",
                ["any user who can read parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Assessment data inherits parent risk authorization.",
                False,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Committee Decision and Authority Level",
        description="Decision and escalation expectations across Authority Level.",
        rules=[
            _rule(
                "Committee Decision and Authority Level",
                "LOW Authority Level Decision",
                ["active members of Board of Origin / LOW operational committee"],
                "LOW",
                "Active committee membership",
                "Decision scope is limited to the LOW operational committee path.",
                True,
            ),
            _rule(
                "Committee Decision and Authority Level",
                "MIDDLE Authority Level Decision",
                ["active members of Risk Management Committee"],
                "MIDDLE",
                "Fixed Governance Committee membership",
                "Decision scope follows Risk Management Committee authority.",
                True,
            ),
            _rule(
                "Committee Decision and Authority Level",
                "HIGH Authority Level Decision",
                ["active members of Executive Safety Management Committee"],
                "HIGH",
                "Fixed Governance Committee membership",
                "Decision scope follows executive SMS governance authority.",
                True,
            ),
            _rule(
                "Committee Decision and Authority Level",
                "Escalate Risk",
                ["authorized committee members under current decision workflow"],
                "LOW / MIDDLE / HIGH",
                "Existing decision workflow and Authority Level",
                "Escalation must follow the risk decision path.",
                True,
            ),
            _rule(
                "Committee Decision and Authority Level",
                "Accept Residual Risk",
                ["appropriate Authority Level based on risk severity and escalation status"],
                "LOW / MIDDLE / HIGH",
                "Risk severity, tolerability, and escalation status",
                "Acceptance must be made at the appropriate Authority Level.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Mitigation Actions",
        description="Mitigation action access follows the parent risk and assignment.",
        rules=[
            _rule(
                "Mitigation Actions",
                "Create Risk Action",
                ["users authorized for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Parent risk must be accessible.",
                True,
            ),
            _rule(
                "Mitigation Actions",
                "Update Risk Action",
                ["action owner", "authorized risk owner/governance user if existing rules allow"],
                "LOW / MIDDLE / HIGH",
                "Action assignment and parent risk authorization",
                "Changes must preserve mitigation traceability.",
                True,
            ),
            _rule(
                "Mitigation Actions",
                "Complete Risk Action",
                ["action owner", "authorized governance user"],
                "LOW / MIDDLE / HIGH",
                "Action assignment and parent risk authorization",
                "Completion must include appropriate closure context.",
                True,
            ),
            _rule(
                "Mitigation Actions",
                "Read Risk Actions",
                ["users who can read parent risk", "assigned action owner"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record or action ownership",
                "Action details inherit parent risk authorization.",
                False,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Monitoring Reviews",
        description="Monitoring review access follows the parent risk and monitoring owner.",
        rules=[
            _rule(
                "Monitoring Reviews",
                "Create Monitoring Review",
                ["authorized users for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Parent risk must be accessible.",
                True,
            ),
            _rule(
                "Monitoring Reviews",
                "Complete Monitoring Review",
                ["monitoring owner", "authorized governance user"],
                "LOW / MIDDLE / HIGH",
                "Monitoring assignment and parent risk authorization",
                "Review completion must remain linked to parent risk.",
                True,
            ),
            _rule(
                "Monitoring Reviews",
                "Close Monitoring Review",
                ["monitoring owner", "authorized governance user"],
                "LOW / MIDDLE / HIGH",
                "Monitoring assignment and parent risk authorization",
                "Closure must preserve audit integrity.",
                True,
            ),
            _rule(
                "Monitoring Reviews",
                "Read Monitoring Review",
                ["users who can read parent risk", "monitoring owner"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record or monitoring assignment",
                "Monitoring details inherit parent risk authorization.",
                False,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Evidence and Attachments",
        description="Evidence access is governed by the parent risk record.",
        rules=[
            _rule(
                "Evidence and Attachments",
                "Upload Evidence",
                ["users authorized for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Parent risk must be accessible.",
                True,
            ),
            _rule(
                "Evidence and Attachments",
                "Read/Download Evidence",
                ["users authorized for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Evidence must not be exposed outside parent risk authorization.",
                False,
                "Track downloads if future audit policy requires it.",
            ),
            _rule(
                "Evidence and Attachments",
                "Archive Evidence",
                ["authorized governance/admin role if implemented"],
                "LOW / MIDDLE / HIGH",
                "Archive Policy and evidence governance",
                "Evidence remains traceable; no hard delete in MVP.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Reports and Exports",
        description=(
            "Reports and exports must preserve the on-screen authorization "
            "boundary."
        ),
        rules=[
            _rule(
                "Reports and Exports",
                "Generate Risk Dossier",
                ["users authorized for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Parent risk must be accessible.",
                True,
            ),
            _rule(
                "Reports and Exports",
                "Download Generated Report",
                ["users authorized for the underlying risk/report context"],
                "LOW / MIDDLE / HIGH",
                "Readable underlying risk or report context",
                "Download must not expose an unreadable risk context.",
                False,
                "Audit depends on report tracking policy.",
            ),
            _rule(
                "Reports and Exports",
                "Export Risk Register",
                ["authenticated active users"],
                "LOW / MIDDLE / HIGH",
                "Existing authorized risk list flow",
                "Export must include only risks readable by that user.",
                True,
                "Authorization boundary must match UI risk list access.",
            ),
            _rule(
                "Reports and Exports",
                "Export Audit Trail",
                ["authorized audit/admin/governance users under existing audit access rules"],
                "LOW / MIDDLE / HIGH",
                "Audit query access rules and readable entity scope",
                "Audit export must not include unreadable entity context.",
                True,
            ),
            _rule(
                "Reports and Exports",
                "Export Evidence Package",
                ["users authorized for parent risk"],
                "LOW / MIDDLE / HIGH",
                "Readable parent risk record",
                "Package must include only evidence in authorized parent risk context.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Committee Meetings",
        description="Committee meeting access follows committee governance rules.",
        rules=[
            _rule(
                "Committee Meetings",
                "Create Meeting",
                ["authorized committee/governance user"],
                "LOW / MIDDLE / HIGH",
                "Committee membership and governance workflow",
                "Committee context must be authorized.",
                True,
            ),
            _rule(
                "Committee Meetings",
                "Update Draft Meeting",
                ["authorized committee/governance user"],
                "LOW / MIDDLE / HIGH",
                "Committee membership and draft status",
                "Finalized minutes should not be casually edited.",
                True,
            ),
            _rule(
                "Committee Meetings",
                "Finalize Meeting Minutes",
                ["authorized committee/governance user"],
                "LOW / MIDDLE / HIGH",
                "Committee membership and finalization workflow",
                "Finalization creates governed committee records.",
                True,
            ),
            _rule(
                "Committee Meetings",
                "Read Meeting Minutes",
                ["committee members", "governance users under existing access rules"],
                "LOW / MIDDLE / HIGH",
                "Committee membership and governance visibility",
                "Minutes must not expose unauthorized committee context.",
                False,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Admin Governance",
        description="Administrative governance actions remain restricted.",
        rules=[
            _rule(
                "Admin Governance",
                "Manage Users",
                ["admin only"],
                None,
                "Admin governance authorization",
                "Admin governance actions must remain restricted.",
                True,
            ),
            _rule(
                "Admin Governance",
                "Manage Roles",
                ["admin only"],
                None,
                "Admin governance authorization",
                "Role changes must preserve least privilege.",
                True,
            ),
            _rule(
                "Admin Governance",
                "Manage Committees",
                ["admin only"],
                "LOW / MIDDLE / HIGH",
                "Admin governance authorization",
                "Fixed MIDDLE/HIGH committees protected.",
                True,
                "Fixed Governance Committee configuration must not be weakened.",
            ),
            _rule(
                "Admin Governance",
                "Manage Memberships",
                ["admin only"],
                "LOW / MIDDLE / HIGH",
                "Admin governance authorization",
                "Membership changes affect access boundaries.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Data Retention / Archive / Restore",
        description="Retention, archive, and restore access must preserve audit integrity.",
        rules=[
            _rule(
                "Data Retention / Archive / Restore",
                "View Retention Policy",
                ["authenticated active users"],
                None,
                "Authenticated active user",
                "Policy visibility only; no governed record mutation.",
                False,
            ),
            _rule(
                "Data Retention / Archive / Restore",
                "Archive Governed Record",
                ["admin/governance authority only when implemented"],
                "LOW / MIDDLE / HIGH",
                "Archive Policy and governance authority",
                "No legal/investigation hold and no hard delete.",
                True,
            ),
            _rule(
                "Data Retention / Archive / Restore",
                "Restore Governed Record",
                ["admin/governance authority only"],
                "LOW / MIDDLE / HIGH",
                "Archive Policy and governance authority",
                "Restore must be justified and auditable.",
                True,
            ),
        ],
    ),
    PermissionMatrixSection(
        section="Backup and Restore",
        description="Operational backup and restore duties are outside app workflows.",
        rules=[
            _rule(
                "Backup and Restore",
                "View Backup Procedure",
                ["authenticated active users", "documented-only readers"],
                None,
                "Documentation access",
                "Procedure does not grant operational backup rights.",
                False,
            ),
            _rule(
                "Backup and Restore",
                "Execute Backup Script",
                ["system operator", "IT", "authorized admin outside app"],
                None,
                "Company IT/security operating procedure",
                "Backups contain sensitive SMS data.",
                False,
                "Outside app, but execution should be controlled and documented.",
            ),
            _rule(
                "Backup and Restore",
                "Restore Backup",
                ["system operator", "IT", "authorized admin with approval"],
                None,
                "Company IT/security approval and restore procedure",
                "Production restore requires approval and documented restore log.",
                True,
                "Outside app plus governance record.",
            ),
        ],
    ),
]


def get_permission_matrix() -> PermissionMatrix:
    return PermissionMatrix(
        policy_name=POLICY_NAME,
        policy_version=POLICY_VERSION,
        effective_status=EFFECTIVE_STATUS,
        generated_at=datetime.now(timezone.utc),
        summary=(
            "Draft MVP Permission Matrix for Access Control across Authority "
            "Level, LOW, MIDDLE, HIGH, Board of Origin, Fixed Governance "
            "Committee oversight, SMS governance, exports, archive/restore, "
            "and Audit integrity."
        ),
        principles=PRINCIPLES,
        sections=SECTIONS,
    )
