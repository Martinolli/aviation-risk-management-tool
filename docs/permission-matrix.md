# Permission Matrix and Access Control Policy

## Purpose

This Permission Matrix and Access Control Policy defines access control expectations for governed SMS records in the Aviation Risk Management Tool. It documents who can read, create, update, decide, export, archive, restore, administer, and review records across Authority Level, including LOW, MIDDLE, HIGH, Board of Origin, and Fixed Governance Committee oversight.

## Scope

This policy covers:

- Authentication
- Risk records
- Risk assessments
- Committee decisions
- Mitigation actions
- Monitoring reviews
- Evidence
- Reports and exports
- Committee meetings
- Admin governance
- Data retention/archive/restore
- Backup/restore

## Core Principles

- Authenticated active users only.
- Authority Level matters.
- Board of Origin controls operational review.
- Fixed MIDDLE/HIGH governance committees provide oversight.
- Exports must respect the same authorization boundaries as UI access.
- Archive/restore must preserve audit integrity.
- No hard delete for governed SMS records.
- Admin actions must be restricted.
- Access control must support SMS governance, not bypass it.

## Permission Matrix

| Area | Capability | Allowed Users / Roles | Authority Level | Access Basis | Restrictions | Audit Expected |
| --- | --- | --- | --- | --- | --- | --- |
| Authentication and Session | Login | Active users with valid credentials | N/A | JWT authentication after credential validation | Inactive users denied. | No |
| Authentication and Session | Current User / Session Check | Authenticated active users | N/A | Bearer token current-user dependency | Invalid, expired, or inactive sessions denied. | No |
| Risk Record Access | Create Risk Record | Authenticated active users | Usually LOW / Board of Origin assignment before submission | Authenticated active user creates the initial governed record | Board of Origin should be assigned before submission. | Yes |
| Risk Record Access | Read Risk Record | Creator, owner, Board of Origin active committee members, assigned assessor, assigned action owner, decision maker, committee members linked to decisions, fixed MIDDLE/HIGH governance members | LOW / MIDDLE / HIGH | Existing risk access service and related-record links | Read access must not expose unauthorized records. | No for ordinary read; audit expected for export/report generation |
| Risk Record Access | Update Draft Risk Record | Creator, owner, authorized operational users before submission | LOW | Existing update workflow and ownership checks | Avoid editing closed/accepted governed records except through controlled workflows. | Yes |
| Risk Record Access | Submit Risk Record | Creator, owner, authorized board member under existing rules | LOW / Board of Origin | Existing submission workflow | Submission follows the configured Board of Origin path. | Yes |
| Risk Record Access | Archive Risk Record | Admin or authorized governance role if implemented | LOW / MIDDLE / HIGH | Archive Policy and governance authority | No open Legal / Investigation Hold and no casual hard delete. | Yes |
| Risk Record Access | Restore Risk Record | Admin or authorized governance role if implemented | LOW / MIDDLE / HIGH | Archive Policy and governance authority | Restore must be justified and controlled. | Yes |
| Risk Assessment | Create Initial Assessment | Authorized users for readable risk records | LOW / MIDDLE / HIGH | Readable parent risk record | Risk must be accessible. | Yes |
| Risk Assessment | Create Residual Assessment | Authorized users for readable risk records after mitigations | LOW / MIDDLE / HIGH | Readable parent risk record and mitigation workflow context | Risk must be accessible. | Yes |
| Risk Assessment | Read Assessments | Any user who can read parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Assessment data inherits parent risk authorization. | No |
| Committee Decision and Authority Level | LOW Authority Level Decision | Active members of Board of Origin / LOW operational committee | LOW | Active committee membership | Decision scope is limited to the LOW operational committee path. | Yes |
| Committee Decision and Authority Level | MIDDLE Authority Level Decision | Active members of Risk Management Committee | MIDDLE | Fixed Governance Committee membership | Decision scope follows Risk Management Committee authority. | Yes |
| Committee Decision and Authority Level | HIGH Authority Level Decision | Active members of Executive Safety Management Committee | HIGH | Fixed Governance Committee membership | Decision scope follows executive SMS governance authority. | Yes |
| Committee Decision and Authority Level | Escalate Risk | Authorized committee members under current decision workflow | LOW / MIDDLE / HIGH | Existing decision workflow and Authority Level | Escalation must follow the risk decision path. | Yes |
| Committee Decision and Authority Level | Accept Residual Risk | Appropriate Authority Level based on risk severity and escalation status | LOW / MIDDLE / HIGH | Risk severity, tolerability, and escalation status | Acceptance must be made at the appropriate Authority Level. | Yes |
| Mitigation Actions | Create Risk Action | Users authorized for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Parent risk must be accessible. | Yes |
| Mitigation Actions | Update Risk Action | Action owner, authorized risk owner/governance user if existing rules allow | LOW / MIDDLE / HIGH | Action assignment and parent risk authorization | Changes must preserve mitigation traceability. | Yes |
| Mitigation Actions | Complete Risk Action | Action owner or authorized governance user | LOW / MIDDLE / HIGH | Action assignment and parent risk authorization | Completion must include appropriate closure context. | Yes |
| Mitigation Actions | Read Risk Actions | Users who can read parent risk, assigned action owner | LOW / MIDDLE / HIGH | Readable parent risk record or action ownership | Action details inherit parent risk authorization. | No |
| Monitoring Reviews | Create Monitoring Review | Authorized users for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Parent risk must be accessible. | Yes |
| Monitoring Reviews | Complete Monitoring Review | Monitoring owner or authorized governance user | LOW / MIDDLE / HIGH | Monitoring assignment and parent risk authorization | Review completion must remain linked to parent risk. | Yes |
| Monitoring Reviews | Close Monitoring Review | Monitoring owner or authorized governance user | LOW / MIDDLE / HIGH | Monitoring assignment and parent risk authorization | Closure must preserve audit integrity. | Yes |
| Monitoring Reviews | Read Monitoring Review | Users who can read parent risk, monitoring owner | LOW / MIDDLE / HIGH | Readable parent risk record or monitoring assignment | Monitoring details inherit parent risk authorization. | No |
| Evidence and Attachments | Upload Evidence | Users authorized for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Parent risk must be accessible. | Yes |
| Evidence and Attachments | Read/Download Evidence | Users authorized for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Evidence must not be exposed outside parent risk authorization. | No unless future download audit policy requires it |
| Evidence and Attachments | Archive Evidence | Authorized governance/admin role if implemented | LOW / MIDDLE / HIGH | Archive Policy and evidence governance | Evidence remains traceable; no hard delete in MVP. | Yes |
| Reports and Exports | Generate Risk Dossier | Users authorized for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Parent risk must be accessible. | Yes |
| Reports and Exports | Download Generated Report | Users authorized for the underlying risk/report context | LOW / MIDDLE / HIGH | Readable underlying risk or report context | Download must not expose an unreadable risk context. | No unless report tracking policy requires it |
| Reports and Exports | Export Risk Register | Authenticated active users | LOW / MIDDLE / HIGH | Existing authorized risk list flow | Export must include only risks readable by that user. | Yes if export generation is tracked, otherwise recommended |
| Reports and Exports | Export Audit Trail | Authorized audit/admin/governance users under existing audit access rules | LOW / MIDDLE / HIGH | Audit query access rules and readable entity scope | Audit export must not include unreadable entity context. | Yes |
| Reports and Exports | Export Evidence Package | Users authorized for parent risk | LOW / MIDDLE / HIGH | Readable parent risk record | Package must include only evidence in authorized parent risk context. | Yes |
| Committee Meetings | Create Meeting | Authorized committee/governance user | LOW / MIDDLE / HIGH | Committee membership and governance workflow | Committee context must be authorized. | Yes |
| Committee Meetings | Update Draft Meeting | Authorized committee/governance user | LOW / MIDDLE / HIGH | Committee membership and draft status | Finalized minutes should not be casually edited. | Yes |
| Committee Meetings | Finalize Meeting Minutes | Authorized committee/governance user | LOW / MIDDLE / HIGH | Committee membership and finalization workflow | Finalization creates governed committee records. | Yes |
| Committee Meetings | Read Meeting Minutes | Committee members / governance users under existing access rules | LOW / MIDDLE / HIGH | Committee membership and governance visibility | Minutes must not expose unauthorized committee context. | No |
| Admin Governance | Manage Users | Admin only | N/A | Admin governance authorization | Admin governance actions must remain restricted. | Yes |
| Admin Governance | Manage Roles | Admin only | N/A | Admin governance authorization | Role changes must preserve least privilege. | Yes |
| Admin Governance | Manage Committees | Admin only | LOW / MIDDLE / HIGH | Admin governance authorization | Fixed MIDDLE/HIGH committees protected. | Yes |
| Admin Governance | Manage Memberships | Admin only | LOW / MIDDLE / HIGH | Admin governance authorization | Membership changes affect access boundaries. | Yes |
| Data Retention / Archive / Restore | View Retention Policy | Authenticated active users | N/A | Authenticated active user | Policy visibility only; no governed record mutation. | No |
| Data Retention / Archive / Restore | Archive Governed Record | Admin/governance authority only when implemented | LOW / MIDDLE / HIGH | Archive Policy and governance authority | No legal/investigation hold and no hard delete. | Yes |
| Data Retention / Archive / Restore | Restore Governed Record | Admin/governance authority only | LOW / MIDDLE / HIGH | Archive Policy and governance authority | Restore must be justified and auditable. | Yes |
| Electronic Approval | Create Electronic Approval for Risk Record | Authenticated active users who can read the risk record | LOW / MIDDLE / HIGH | Existing risk access service and Authority Level context | This is a Controlled Approval Record, Not a cryptographic digital signature. | Yes |
| Electronic Approval | Create Electronic Approval for Risk Decision | Decision maker, active member of the decision committee, or fixed MIDDLE/HIGH governance member with readable parent risk access | LOW / MIDDLE / HIGH | Decision committee membership, fixed governance oversight, and readable parent risk | Approval must stay within existing Access Control and Authority Level boundaries. | Yes |
| Electronic Approval | Read Electronic Approval | Users who can read the associated risk record or decision context | LOW / MIDDLE / HIGH | Parent risk read authorization | Approval records must not expose unreadable governed records. | No for ordinary read |
| Backup and Restore | View Backup Procedure | Authenticated active users or documented-only readers | N/A | Documentation access | Procedure does not grant operational backup rights. | No |
| Backup and Restore | Execute Backup Script | System operator / IT / authorized admin outside app | N/A | Company IT/security operating procedure | Backups contain sensitive SMS data. | Outside app, but should be controlled and documented |
| Backup and Restore | Restore Backup | System operator / IT / authorized admin with approval | N/A | Company IT/security approval and restore procedure | Production restore requires approval and documented restore log. | Outside app plus governance record |

## Authority Level Interpretation

- LOW: Operational board / domain committee authority.
- MIDDLE: Risk Management Committee oversight/consolidation authority.
- HIGH: Executive Safety Management Committee / accountable management authority.

## Board of Origin Rule

The Board of Origin defines the first committee ownership and normal LOW-level access path for the risk. Active members of that LOW operational committee can review risks assigned to that board according to current system rules.

## Fixed Governance Committee Rule

Fixed MIDDLE/HIGH governance members may have broader oversight visibility according to current system rules. This supports SMS governance review, escalation oversight, audit preparation, and executive safety management visibility.

## Export Access Rule

Exports must never include records the requesting user cannot read. Risk register exports, audit exports, evidence packages, and generated reports must preserve the same authorization boundaries as UI access.

## Operational Logs Access Rule

Logs may contain operational metadata and should be accessible only to authorized IT/admin personnel. Safe Logging must avoid secrets, request bodies, JWT tokens, passwords, database URLs, and evidence contents. Logs support Operational Diagnostics and do not replace the Audit Trail.

## Archive and Restore Access Rule

Archive/restore must be controlled, justified, and auditable. Governed SMS records should be archived instead of hard-deleted, and archive/restore actions must preserve audit integrity and evidence traceability.

## Electronic Approval Rule

Electronic Approval records may be created only by authenticated active users within existing Access Control and Authority Level boundaries. Risk record approvals require readable risk access. Risk decision approvals require readable parent risk access plus decision-maker, decision committee, or fixed MIDDLE/HIGH governance authority. The Electronic Approval / Signature Concept is a Controlled Approval Record for SMS governance and Audit integrity, Not a cryptographic digital signature.

## Known MVP Limitations

- No external identity provider.
- No SSO.
- No database row-level security.
- No cryptographic electronic signatures.
- No legal hold workflow flag yet.
- Permission matrix is draft for SMS governance review.

## Future Improvements

- Configurable permission matrix
- Role-based UI management
- Approval workflow for archive/restore
- Electronic approval/signature
- Legal hold flag
- Fine-grained export permissions
- Row-level security review

## SMS Governance Note

"The permission matrix supports SMS governance, audit integrity, committee authority, and evidence traceability. Final access rules must be approved by company SMS, Quality, IT/cybersecurity, and applicable airworthiness governance functions."
