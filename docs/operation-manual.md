# Aviation Risk Management Tool — Operation Manual / User Guide

## Document Metadata

| Field | Value |
| --- | --- |
| Document Type | Operation Manual / User Guide |
| Application | Aviation Risk Management Tool |
| Version | 0.1 MVP / Pilot Release Candidate |
| Status | Draft for SMS governance review |
| Intended Users | SMS personnel, risk owners, committee members, administrators, management users, audit/governance reviewers |

Related Documents:

- [Deployment Readiness Guide](deployment-readiness.md)
- [Backup and Restore Procedure](backup-and-restore.md)
- [Data Retention and Archive Policy](data-retention-and-archive-policy.md)
- [Permission Matrix](permission-matrix.md)
- [Electronic Approval Concept](electronic-approval-concept.md)
- [User Acceptance Test Pack](user-acceptance-test-pack.md)
- [Pilot Deployment Checklist](pilot-deployment-checklist.md)
- [Pilot Execution Support Pack](pilot-execution-support-pack.md)
- [Post-Pilot Feedback and Defect Register](post-pilot-feedback-and-defect-register.md)

## 1. Introduction

This Operation Manual / User Guide supports Normal Operation of the Aviation Risk Management Tool during pilot/internal use. It explains the application purpose, user roles, Authority Level model, Board of Origin routing, feature-by-feature operation, governance workflow, limitations, and release-readiness references.

The manual is a controlled Markdown document for version control. It is draft guidance until reviewed and accepted by company SMS, Quality, IT/cybersecurity, and governance stakeholders.

## 2. Purpose of the Application

The Aviation Risk Management Tool supports structured SMS risk management, risk recording, assessment, governance review, mitigation tracking, monitoring, evidence preservation, reporting, and audit preparation. It is intended to help authorized users move a risk from initial Problem Description through package completion, initial risk assessment, committee decision, mitigation action tracking, residual risk assessment, monitoring, reporting, and auditable governance review.

## 3. Scope of Use

The tool supports:

- Operational risk records.
- Engineering/manufacturing/quality/flight test risk governance.
- Committee review.
- Risk mitigation follow-up.
- Monitoring and closure.
- Evidence and report traceability.

The tool does not replace regulatory obligations, formal SMS manual requirements, quality management system procedures, airworthiness requirements, legal review, or accountable manager authority.

## 4. Key Concepts

| Concept | Meaning |
| --- | --- |
| Problem Description | The original/root description of the risk issue being evaluated. |
| Hazard | A condition or source with the potential to cause harm or adverse operational effect. |
| Central Event | The main event that links causes to consequences in the risk scenario. |
| Causes | Factors that may lead to the central event. |
| Consequences | Potential outcomes if the central event occurs. |
| Existing Controls | Controls already in place before new mitigation actions are added. |
| Risk Assessment | Severity and likelihood evaluation using the approved risk matrix. |
| Initial Risk | Risk level before planned additional mitigation actions. |
| Residual Risk | Risk level after mitigation actions and controls are considered. |
| Mitigation Action | Assigned activity intended to reduce likelihood, severity, exposure, or uncertainty. |
| Monitoring Review | Periodic review of an accepted or active risk to confirm continued control effectiveness. |
| Board of Origin | The originating operational board or committee responsible for first-level review. |
| Authority Level | Governance level for decision authority: LOW, MIDDLE, or HIGH. |
| Electronic Approval | Controlled Approval Record created by an authenticated user for a target record or decision. |
| Audit Trail | Application audit record of meaningful governed actions. |
| Controlled Export | Download generated from authorized system data with access boundaries applied. |
| No Hard Delete | Governance principle that controlled SMS records should be archived/inactivated instead of physically deleted. |

## 5. User Roles and Authority Level

| Role | Normal responsibility |
| --- | --- |
| System Administrator | Manages users, roles, committees, membership, and governed admin configuration. |
| SMS / Risk Owner | Creates and maintains risk records, packages, assessments, mitigations, evidence, and reports. |
| LOW Authority Level committee member | Performs Board of Origin / operational board decisions. |
| MIDDLE Authority Level Risk Management Committee member | Provides Risk Management Committee oversight, consolidation, and escalation decisions. |
| HIGH Authority Level Executive Safety Management Committee member | Provides executive safety/accountable management level review and acceptance. |
| Action Owner | Completes assigned mitigation actions. |
| Monitoring Owner | Completes assigned monitoring reviews. |
| Management Viewer | Reviews management dashboard summaries and governance follow-up indicators. |
| Audit / Governance Reviewer | Reviews audit trail, exports, approvals, evidence traceability, and controlled documentation. |

Authority Level interpretation:

- LOW: Operational Board / Board of Origin.
- MIDDLE: Risk Management Committee oversight and consolidation.
- HIGH: Executive Safety Management Committee / accountable management level.

Users must act only within their assigned role, membership, Board of Origin, and Authority Level boundaries.

## 6. Access and Login

Users access the application through the login page. After authentication, the application uses the current user endpoint to determine identity, role, active status, committee membership, and Authority Level context.

Inactive users cannot operate the application. Development fallback authentication must remain disabled in production or any controlled pilot environment. Session behavior should be verified at the start of UAT, pilot deployment, and Normal Operation.

## 7. Application Navigation

Main navigation may include:

- Dashboard
- Management
- Notifications
- Risks
- My Queue
- My Actions
- My Monitoring
- Meeting Packs
- Meetings
- Reports
- Audit Trail
- Permission Matrix
- Retention Policy
- Admin

Available navigation depends on authentication, role, Authority Level, and authorization rules.

## 8. Dashboard Overview

The operational dashboard supports day-to-day risk management. It may show open risks, drafts, workflow status, monitoring snapshot, action due-date snapshot, recent risks, and attention items. Users should treat dashboard values as operational indicators and open the source risk records before making governed decisions.

## 9. Management Dashboard

The management dashboard provides a management-level view for executive summary, high risk exposure, committee backlog, overdue actions, monitoring concerns, domain hotspots, and governance follow-up. It supports oversight and prioritization but does not replace committee review, SMS governance approval, or the Audit Trail.

## 10. Risk Records

Risk Records are the primary governed objects. A risk record includes a Risk ID, Problem Description, Domain, Board of Origin, workflow status, lifecycle status, owner, creator, draft state, and archived/inactive visibility where applicable.

To create a risk, an authorized SMS / Risk Owner opens Risks, selects the create action, enters the Problem Description, selects the Domain, confirms the Board of Origin if required, and saves the record. New records normally begin in DRAFT with lifecycle status OPEN.

## 11. Risk Package Completion

A complete risk package should include:

- Problem Description.
- Domain.
- Board of Origin.
- Hazard statement.
- Central event.
- Causes.
- Consequences.
- Existing controls.
- Initial assessment readiness.

Risk package completion supports consistent committee review and helps prevent incomplete submission.

## 12. Initial Risk Assessment

Initial risk assessment records severity, likelihood, risk level, rationale, matrix calculation, mitigation requirement, escalation requirement, and tolerability. The assessment should use the seeded and approved risk matrix. If the initial risk is not tolerable or exceeds a committee's Authority Level, mitigation and/or escalation may be required.

## 13. Risk Submission Workflow

Typical workflow states include:

- Draft.
- Submitted to Operational Board.
- Under Operational Board Review.
- Escalated to Risk Management Committee.
- Escalated to Executive Committee.
- Accepted.
- Rejected.
- Returned for Revision.
- Closed.

Only complete records should be submitted to the Board of Origin. Returned records should be updated by the risk owner and resubmitted according to SMS governance expectations.

## 14. Committee Decision Process

Committee users work from a decision queue or an assigned risk view. Decision authority is governed by Authority Level, Board of Origin membership, and fixed governance committee rules.

Decision concepts include:

- Board of Origin LOW decision.
- MIDDLE fixed governance committee review.
- HIGH fixed governance committee review.
- Approve.
- Reject.
- Escalate.
- Return for revision.
- Accept residual risk.
- Close.

Lower Authority Level users must not decide higher Authority Level risks. Decisions should include rationale and should preserve Audit integrity.

## 15. Mitigation Actions

Mitigation actions are created against a risk record, assigned to an Action Owner, given a due date, and tracked by status. Normal statuses include Open, In Progress, Completed, Cancelled, and overdue/due soon behavior where supported.

Action Owners should use My Actions to review assigned work. Completion should include practical completion notes and evidence reference where appropriate.

## 16. Residual Risk Assessment

Residual risk assessment is required when mitigation actions or new controls affect the risk profile, or when a committee requires confirmation of tolerability after mitigation. Residual assessment should relate clearly to mitigation actions and remaining controls.

If residual risk remains non-tolerable, the risk may require further mitigation, escalation, or executive acceptance according to Authority Level rules.

## 17. Monitoring and Review Cycle

Monitoring reviews confirm that accepted or active risks remain controlled over time. A monitoring review includes a Monitoring Owner, review frequency or due date, next review date, and status such as Active, Due, Overdue, Closed, or Cancelled.

Monitoring Owners use My Monitoring to complete reviews. Completing a review should record outcome, notes, and any required follow-up. Monitoring may be closed only when governance criteria are satisfied.

## 18. Evidence Management

Evidence management supports upload evidence, evidence description, file storage, Evidence traceability, evidence archive concept, No Hard Delete principle, and Risk Evidence Package export.

Evidence should be approved for the environment and data classification. Do not upload classified, export-controlled, or sensitive investigation evidence during UAT or pilot use unless approved. Evidence records should remain traceable to the risk, uploader, timestamp, and related governance action.

## 19. Reports and Exports

Reports and exports include:

- Risk Dossier Report.
- Committee Meeting Pack.
- Committee Meeting Minutes.
- Risk Evidence Package ZIP.
- Risk Register CSV/DOCX.
- Audit Trail CSV/DOCX.

Controlled Export means the export is generated from system data and authorization boundaries apply. Exports must not bypass risk visibility, Authority Level, committee membership, or audit access rules.

## 20. Committee Meeting Packs

Committee Meeting Packs prepare committee members before meetings. A pack may include decision queue summary, action follow-up, monitoring follow-up, evidence summary, and related risk information. Packs should be generated from controlled system data and reviewed before the meeting.

## 21. Committee Meeting Minutes

Committee meeting records may include draft meeting details, attendees, risk items, finalized minutes, decision record, and audit/governance use. Finalized minutes should reflect committee decisions and should not be manually reconstructed outside controlled records when the application can generate or preserve them.

## 22. Notifications

Notifications alert users to assigned or relevant work. Categories may include action alerts, monitoring alerts, decision queue alerts, meeting alerts, and severity levels. Users should review notifications daily and open the source record before acting.

## 23. Audit Trail

The Audit Trail records meaningful governed actions such as risk creation, updates, submissions, decisions, evidence actions, report generation, exports, approvals, admin changes, and workflow transitions where implemented.

Audit integrity matters because SMS governance decisions must be traceable to actor, time, target record, action, and context. Audit exports support review. The Audit Trail is separate from operational logs: audit records support governance traceability, while operational logs support technical troubleshooting.

## 24. Admin Governance Management

Admin governance includes user management, role management, committee management, membership management, and fixed committee protection. LOW committees are configurable by administrators where supported. MIDDLE and HIGH fixed committees are protected and must not be deleted or improperly modified.

Admin functions are admin-only and should be performed under approved governance direction.

## 25. Permission Matrix

The Permission Matrix summarizes who can read, decide, export, archive/restore, and administer records. It defines Authority Level interpretation, Board of Origin access, fixed governance committee oversight, export authorization boundaries, and approval visibility.

See [Permission Matrix](permission-matrix.md).

## 26. Data Retention and Archive Policy

The Data Retention and Archive Policy defines No Hard Delete, archive instead of delete, evidence preservation, audit log preservation, Legal / Investigation Hold, and restore expectations. Governed SMS records should be archived/inactivated instead of physically deleted.

See [Data Retention and Archive Policy](data-retention-and-archive-policy.md).

## 27. Electronic Approval / Signature Concept

Electronic Approval creates a Controlled Approval Record for an authenticated user, timestamp, target record, Authority Level, acknowledgement, approval hash, and Audit Trail entry. It supports SMS governance traceability and Audit integrity.

The MVP concept is not a cryptographic digital signature and is not a certified legal e-signature. Final validity and use must be approved by company governance functions.

See [Electronic Approval Concept](electronic-approval-concept.md).

## 28. Backup and Restore Procedure

Backup and restore readiness includes database backup, evidence backup, generated reports backup, restore procedure, and backup verification. Backups should be taken before pilot use when persistent data is used.

See [Backup and Restore Procedure](backup-and-restore.md).

## 29. Production Logging / Request ID

Production logging preparation includes Request ID correlation, `X-Request-ID` response header where supported, safe logging, health/readiness diagnostics, and sensitive data avoidance. Logs do not replace audit trail records.

Use `/health` for basic service availability and `/health/readiness` for safe readiness diagnostics. Do not expose JWT secrets, passwords, database URLs, or evidence contents in logs.

See [Production Logging / Request ID](production-logging-and-monitoring.md).

## 30. User Acceptance Testing

The User Acceptance Test Pack defines manual UAT scenarios, a UAT test matrix, defect log, and UAT sign-off. UAT should be completed before pilot use and feeds into the Pilot Deployment Checklist.

See [User Acceptance Test Pack](user-acceptance-test-pack.md).

## 31. Pilot Deployment Checklist

The Pilot Deployment Checklist records Go / No-Go, environment readiness, CI readiness, backup readiness, UAT sign-off, Rollback Plan review, Post-Deployment Monitoring ownership, and pilot limitations.

See [Pilot Deployment Checklist](pilot-deployment-checklist.md).

## 32. Post-Pilot Feedback Process

The post-pilot feedback process defines how Post-Pilot Feedback, Defect Register items, Observation Log entries, Enhancement Request items, Training Need findings, Governance Question items, Severity classification, Disposition decisions, Request ID references, SMS governance concerns, and Audit integrity observations are reviewed after Pilot Execution.

See [Post-Pilot Feedback and Defect Register](post-pilot-feedback-and-defect-register.md).

## 33. Normal Operating Procedures

### Procedure 01 — Login and Session Verification

Purpose: Confirm a user can access the application and verify current user context.
Role: Any active user.
Preconditions: Backend and frontend are running; user account is active.
Steps: Open the application, log in, review current user details, confirm role and Authority Level, navigate to an authorized page.
Expected Result: User session is active and authorization context is correct.
Records / Audit Evidence: Login/session observation; support Request ID if login fails.

### Procedure 02 — Create a New Risk Record

Purpose: Start a governed risk record from an approved Problem Description.
Role: SMS / Risk Owner.
Preconditions: User is logged in and has risk creation access.
Steps: Open Risks, select create, enter Problem Description, select Domain, confirm Board of Origin, save.
Expected Result: Risk ID is assigned; workflow status is Draft; lifecycle status is Open.
Records / Audit Evidence: Risk record and creation Audit Trail entry.

### Procedure 03 — Complete Risk Package

Purpose: Prepare a risk for assessment and submission.
Role: SMS / Risk Owner.
Preconditions: Draft risk exists.
Steps: Open the risk, complete hazard, central event, causes, consequences, existing controls, and readiness fields; save.
Expected Result: Required package elements are retained and ready for initial assessment.
Records / Audit Evidence: Updated risk package and Audit Trail entry.

### Procedure 04 — Perform Initial Risk Assessment

Purpose: Record initial severity, likelihood, and risk level.
Role: SMS / Risk Owner.
Preconditions: Risk package is sufficiently complete; risk matrix is seeded.
Steps: Open assessment area, select severity and likelihood, enter rationale, review matrix result, save.
Expected Result: Initial Risk is calculated and saved with rationale.
Records / Audit Evidence: Initial assessment record and Audit Trail entry.

### Procedure 05 — Submit Risk to Board of Origin

Purpose: Move a complete risk into committee review.
Role: SMS / Risk Owner.
Preconditions: Risk package and initial assessment are complete.
Steps: Open risk, review readiness, select submit, confirm Board of Origin routing.
Expected Result: Risk is submitted to the correct LOW Authority Level Board of Origin.
Records / Audit Evidence: Submission state and Audit Trail entry.

### Procedure 06 — Record LOW Authority Level Committee Decision

Purpose: Record Board of Origin decision.
Role: LOW Authority Level committee member.
Preconditions: Risk is assigned to the user's Board of Origin decision queue.
Steps: Open My Queue, select risk, review package, choose decision, enter rationale, submit.
Expected Result: LOW decision is recorded or escalation/return is triggered.
Records / Audit Evidence: Decision record and Audit Trail entry.

### Procedure 07 — Escalate Risk to MIDDLE Authority Level

Purpose: Route risk to Risk Management Committee oversight.
Role: LOW Authority Level committee member.
Preconditions: Risk requires MIDDLE review.
Steps: Open decision view, choose escalation to MIDDLE, enter rationale, submit.
Expected Result: Risk appears for MIDDLE Authority Level review.
Records / Audit Evidence: Escalation decision and Audit Trail entry.

### Procedure 08 — Record MIDDLE Authority Level Committee Decision

Purpose: Record Risk Management Committee decision.
Role: MIDDLE Authority Level Risk Management Committee member.
Preconditions: Risk is assigned to MIDDLE review.
Steps: Open My Queue, review prior decisions, choose decision, enter rationale, submit.
Expected Result: MIDDLE decision is saved or risk is escalated/returned/accepted as permitted.
Records / Audit Evidence: Decision record and Audit Trail entry.

### Procedure 09 — Escalate Risk to HIGH Authority Level

Purpose: Route risk to executive safety review.
Role: MIDDLE Authority Level Risk Management Committee member.
Preconditions: Risk requires HIGH review.
Steps: Open decision view, choose escalation to HIGH, enter rationale, submit.
Expected Result: Risk appears for HIGH Authority Level review.
Records / Audit Evidence: Escalation decision and Audit Trail entry.

### Procedure 10 — Record HIGH Authority Level Acceptance

Purpose: Record executive acceptance where permitted.
Role: HIGH Authority Level Executive Safety Management Committee member.
Preconditions: Risk is assigned to HIGH review.
Steps: Open My Queue, review risk package and history, select acceptance or allowed decision, enter rationale, submit.
Expected Result: HIGH decision is recorded and visible to authorized users.
Records / Audit Evidence: Executive decision record and Audit Trail entry.

### Procedure 11 — Create Mitigation Action

Purpose: Assign risk reduction work.
Role: SMS / Risk Owner.
Preconditions: Risk is accessible and mitigation is required or useful.
Steps: Open mitigation actions, create action, assign owner, set due date, enter description, save.
Expected Result: Action is assigned and visible to the Action Owner.
Records / Audit Evidence: Mitigation action record and Audit Trail entry.

### Procedure 12 — Complete Mitigation Action

Purpose: Close assigned mitigation work.
Role: Action Owner.
Preconditions: Open action is assigned to the user.
Steps: Open My Actions, select action, update status, enter completion notes/evidence reference, save.
Expected Result: Action is completed and risk mitigation progress updates where supported.
Records / Audit Evidence: Action completion record and Audit Trail entry.

### Procedure 13 — Perform Residual Risk Assessment

Purpose: Evaluate risk after mitigation.
Role: SMS / Risk Owner.
Preconditions: Mitigation actions have been reviewed or completed as required.
Steps: Open residual assessment, select severity and likelihood, enter rationale, review matrix result, save.
Expected Result: Residual Risk is calculated and saved.
Records / Audit Evidence: Residual assessment and Audit Trail entry.

### Procedure 14 — Create Monitoring Review

Purpose: Schedule ongoing risk monitoring.
Role: SMS / Risk Owner or Monitoring Owner.
Preconditions: Risk is eligible for monitoring.
Steps: Open monitoring, create review, assign owner, set next review date/frequency, save.
Expected Result: Monitoring review is assigned and visible in My Monitoring.
Records / Audit Evidence: Monitoring review record and Audit Trail entry.

### Procedure 15 — Complete Monitoring Review

Purpose: Record monitoring outcome.
Role: Monitoring Owner.
Preconditions: Monitoring review is assigned and due/active.
Steps: Open My Monitoring, select review, enter outcome and notes, update status, save.
Expected Result: Review completion is recorded and follow-up is clear.
Records / Audit Evidence: Monitoring review completion and Audit Trail entry.

### Procedure 16 — Upload Supporting Evidence

Purpose: Preserve supporting files for risk governance.
Role: SMS / Risk Owner or authorized evidence contributor.
Preconditions: Evidence is approved for the environment and classification.
Steps: Open risk evidence, select upload, choose file, enter description, save.
Expected Result: Evidence is linked to the risk with Evidence traceability.
Records / Audit Evidence: Evidence metadata and Audit Trail entry.

### Procedure 17 — Generate Risk Dossier Report

Purpose: Generate a controlled report for a risk.
Role: SMS / Risk Owner.
Preconditions: Risk has sufficient data for dossier generation.
Steps: Open risk, select generate dossier, wait for completion, review generated report reference.
Expected Result: Risk Dossier Report is generated for the selected risk.
Records / Audit Evidence: Generated report record and Audit Trail entry.

### Procedure 18 — Export Risk Register

Purpose: Export authorized risk register data.
Role: SMS / Risk Owner or authorized reviewer.
Preconditions: User has export access.
Steps: Open Risks, apply filters if needed, select CSV or DOCX export, review downloaded output.
Expected Result: Export contains only authorized filtered records.
Records / Audit Evidence: Export file reference and Audit Trail entry where supported.

### Procedure 19 — Export Audit Trail

Purpose: Export audit events for governance review.
Role: System Administrator or authorized audit reviewer.
Preconditions: User has audit export access.
Steps: Open Audit Trail, apply filters, export CSV/DOCX, review output.
Expected Result: Audit export reflects selected filters and excludes secrets.
Records / Audit Evidence: Audit export file and export audit event.

### Procedure 20 — Prepare Committee Meeting Pack

Purpose: Prepare controlled committee review material.
Role: Committee member or meeting owner.
Preconditions: Meeting or eligible risk set exists.
Steps: Open meeting pack area, select committee/meeting, generate pack, review contents.
Expected Result: Pack includes authorized risks, actions, monitoring, and evidence summary.
Records / Audit Evidence: Meeting pack report and generation audit event.

### Procedure 21 — Create and Finalize Committee Meeting Minutes

Purpose: Preserve committee attendance, discussion, and decisions.
Role: Committee member or meeting owner.
Preconditions: Committee meeting exists.
Steps: Open meeting, enter attendees and risk items, draft minutes, review, finalize.
Expected Result: Finalized minutes are available for governance review.
Records / Audit Evidence: Meeting minutes and finalization audit event.

### Procedure 22 — Create Electronic Approval

Purpose: Record a Controlled Approval Record.
Role: Authorized approver.
Preconditions: User can access the target risk or decision.
Steps: Open target record, select electronic approval, review acknowledgement, submit.
Expected Result: Approval records authenticated user, timestamp, target, Authority Level, acknowledgement, and hash.
Records / Audit Evidence: Electronic Approval record and Audit Trail entry.

### Procedure 23 — Review Notifications

Purpose: Identify assigned work and alerts.
Role: Any active user.
Preconditions: User is logged in.
Steps: Open Notifications, review alerts, open related records, clear or act according to workflow.
Expected Result: User sees relevant authorized notifications only.
Records / Audit Evidence: Source records and any resulting action audit entries.

### Procedure 24 — Review Audit Trail

Purpose: Confirm governed activity traceability.
Role: System Administrator or Audit / Governance Reviewer.
Preconditions: User has audit access.
Steps: Open Audit Trail, search/filter events, review actor/action/entity/time details.
Expected Result: Audit entries support Audit integrity review.
Records / Audit Evidence: Audit Trail view or controlled export.

### Procedure 25 — Admin: Create User

Purpose: Add an approved user account.
Role: System Administrator.
Preconditions: User creation is approved.
Steps: Open Admin, create user, enter email/display name/role/Authority Level, save.
Expected Result: User is created with intended access only.
Records / Audit Evidence: User record and admin Audit Trail entry.

### Procedure 26 — Admin: Assign Committee Membership

Purpose: Assign approved governance membership.
Role: System Administrator.
Preconditions: User and target committee exist.
Steps: Open Admin membership area, select user, assign committee/Board of Origin membership, save.
Expected Result: Membership grants only intended access and decision authority.
Records / Audit Evidence: Membership record and admin Audit Trail entry.

### Procedure 27 — Backup Local Data

Purpose: Preserve local/pilot data before controlled use or maintenance.
Role: IT / Infrastructure Owner.
Preconditions: Backup procedure is approved; storage destination is ready.
Steps: Follow backup procedure for database, evidence uploads, and generated reports.
Expected Result: Backup completes and reference is recorded.
Records / Audit Evidence: Backup output, checksum/verification record, and backup log.

### Procedure 28 — Restore Local Data

Purpose: Restore data in an approved non-production or controlled recovery context.
Role: IT / Infrastructure Owner.
Preconditions: Restore approval exists; target environment is identified.
Steps: Follow restore procedure, restore database/files, verify application health/readiness.
Expected Result: Restored environment is usable and verified.
Records / Audit Evidence: Restore log, backup used, verification result.

### Procedure 29 — Check Health and Readiness

Purpose: Confirm application service and readiness diagnostics.
Role: System Administrator or IT / Infrastructure Owner.
Preconditions: Backend is running.
Steps: Check `/health`, check `/health/readiness`, confirm no secrets are exposed, record result.
Expected Result: Endpoints respond with safe availability/readiness data.
Records / Audit Evidence: Health/readiness result and Request ID if available.

### Procedure 30 — Execute Pilot Deployment Go / No-Go Checklist

Purpose: Confirm controlled readiness before pilot use.
Role: System Owner with SMS, Quality, IT, cybersecurity, and pilot representatives.
Preconditions: UAT is complete; checklist evidence is available.
Steps: Open Pilot Deployment Checklist, review required roles, complete checklist, record Go / No-Go decision, review Rollback Plan and Post-Deployment Monitoring ownership.
Expected Result: Pilot decision is recorded as Go, Go with limitations, No-Go, or rollback required.
Records / Audit Evidence: Completed Pilot Deployment Checklist, Go / No-Go template, sign-off, and limitation record.

## 34. Recommended SMS Operating Cycle

Daily:

- Review notifications.
- Review My Actions.
- Review My Monitoring.
- Check overdue items.

Weekly:

- Review risk dashboard.
- Review new draft/submitted risks.
- Follow up overdue actions.
- Prepare committee agenda/meeting pack if required.

Monthly:

- Management dashboard review.
- Domain hotspot review.
- Monitoring effectiveness review.
- Export risk register if required.
- Review audit trail sample.

Quarterly:

- Review permission matrix.
- Review retention/archive status.
- Review backup/restore evidence.
- Review UAT/pilot feedback.
- Review governance metrics.

Before committee meeting:

- Generate meeting pack.
- Review decision queue.
- Review open actions.
- Review monitoring concerns.
- Prepare minutes shell.

After committee meeting:

- Record decisions.
- Finalize minutes.
- Assign mitigation actions.
- Generate reports/exports if required.
- Record electronic approvals if required.

## 35. Troubleshooting

| Issue | Symptom | Possible cause | User action | Admin / technical action |
| --- | --- | --- | --- | --- |
| Cannot login | Login fails or returns authentication error. | Incorrect credentials, inactive user, backend unavailable, or token issue. | Recheck credentials and report Request ID if shown. | Verify user status, auth configuration, backend logs, and `X-Request-ID`. |
| User inactive | User signs in but cannot operate or access expected pages. | Account deactivated or role removed. | Contact System Administrator. | Review active flag, role, memberships, and audit history. |
| Risk not visible | Expected risk is missing from lists or dashboard. | Authorization boundary, Board of Origin mismatch, archive state, filter, or wrong user. | Clear filters and confirm expected access. | Review Permission Matrix, user memberships, risk owner/committee, and access service behavior. |
| Decision button unavailable | Decision controls are hidden or disabled. | User lacks Authority Level, committee membership, or workflow state is not decision-ready. | Confirm role and queue assignment. | Review workflow status, Authority Level, Board of Origin, and membership. |
| Export fails | CSV/DOCX/ZIP does not download. | Authorization, missing data, report path issue, or backend error. | Retry once and record Request ID. | Check export endpoint, generated reports path, logs, and permissions. |
| Report generation fails | Dossier or pack generation errors. | Missing required risk data, file path issue, or document generation error. | Confirm required data is complete and record Request ID. | Review generated reports directory, logs, and report service error. |
| Evidence upload fails | File upload rejected or does not appear. | File too large, unsupported storage path, network error, or permission issue. | Confirm file is approved and retry with a small test file if allowed. | Check upload size setting, evidence storage path, permissions, and logs. |
| Backend not reachable | API calls fail or browser shows network error. | Backend service down, port blocked, or API URL mismatch. | Record time and page/action. | Check backend process, `/health`, firewall/proxy, and service logs. |
| Frontend cannot connect to API | UI loads but data does not. | `VITE_API_BASE_URL` mismatch, CORS issue, or backend unavailable. | Record visible error and browser. | Verify frontend API base URL, CORS Allowed Origins, backend health, and browser console. |
| Health endpoint fails | `/health` does not respond successfully. | Backend down or dependency/startup issue. | Escalate to support owner. | Review backend process, environment variables, and startup logs. |
| Readiness endpoint fails | `/health/readiness` fails or reports unsafe readiness. | Configuration, storage, or safety validation issue. | Do not proceed with pilot Go / No-Go. | Review readiness fields, production safety settings, storage paths, and logs. |
| Request ID for support | User reports an error without traceability. | Request ID not captured or not shown. | Capture error time, action, user, and any Request ID. | Correlate `X-Request-ID` response header with backend logs. |
| CI failing | Readiness gate is blocked. | Backend, frontend, health smoke, or preview smoke failure. | Do not start pilot based on failed CI. | Review CI logs, fix failure, and rerun checks. |
| Backup script fails | Backup command exits with error. | PostgreSQL credentials, path, missing tool, or permission issue. | Stop pilot readiness until backup is resolved. | Review backup script output, environment, storage path, and database connectivity. |
| Restore script fails | Restore command exits with error or app does not start after restore. | Wrong backup, missing files, DB conflict, or permission issue. | Escalate to IT owner. | Review restore log, backup integrity, database state, evidence/report paths, and health endpoints. |

## 36. Limitations

- MVP / pilot release candidate.
- Not a certified legal e-signature.
- Not a regulatory reporting system by itself.
- Not a replacement for SMS manual.
- No SSO yet.
- No external monitoring provider yet.
- No automated retention scheduler yet.
- No cloud backup automation yet.
- Manual UAT required before pilot use.
- Operation Manual is draft for governance review.

## 37. Release Readiness Notes

Before pilot use, confirm the User Acceptance Test Pack is complete, the Pilot Deployment Checklist has a recorded Go / No-Go decision, critical defects are closed, major defects are reviewed, backups are verified, permission boundaries are reviewed, and health/readiness diagnostics are available.

Before broader production use, company SMS, Quality, IT/cybersecurity, legal, data protection, and airworthiness governance approval must be obtained according to company policy.

### Release Package Reference

Review [Release Notes v1.0](release-notes-v1.0.md), the [Version 1.0 Release Package Checklist](release-package-checklist.md), the [Pilot Execution Support Pack](pilot-execution-support-pack.md), and the [Post-Pilot Feedback and Defect Register](post-pilot-feedback-and-defect-register.md) before creating the proposed pilot release tag, starting controlled pilot execution, or converting pilot findings into follow-up tasks.

## 38. Annex A — Procedure Index

See [operation-procedure-index.csv](templates/operation-procedure-index.csv) for a procedure tracking template covering Procedure 01 through Procedure 30.

## 39. Annex B — Glossary

| Term | Definition |
| --- | --- |
| SMS | Safety Management System. |
| Risk Record | Governed record describing a risk issue, workflow state, assessments, actions, evidence, and decisions. |
| Hazard | Condition or source with potential to cause harm. |
| Central Event | Primary event connecting causes to consequences. |
| Board of Origin | Originating operational board responsible for first-level review. |
| Authority Level | LOW, MIDDLE, or HIGH governance decision level. |
| LOW | Operational Board / Board of Origin authority. |
| MIDDLE | Risk Management Committee authority. |
| HIGH | Executive Safety Management Committee / accountable management authority. |
| Mitigation Action | Assigned action intended to reduce risk. |
| Residual Risk | Risk remaining after mitigation and controls. |
| Monitoring Review | Scheduled review of ongoing risk control effectiveness. |
| Evidence | Supporting file or metadata linked to a governed record. |
| Audit Trail | Governed application record of meaningful actions. |
| Controlled Export | Authorized export generated from controlled system data. |
| Electronic Approval | Controlled Approval Record from an authenticated user. |
| Request ID | Identifier used to correlate requests with technical logs. |
| UAT | User Acceptance Test. |
| Pilot Deployment | Controlled limited-scope deployment before broader operational release. |
| Post-Pilot Feedback | Controlled review of pilot findings after pilot execution. |
| Disposition | Decision recorded against a defect, observation, feedback item, training action, governance action, or future task. |
| No Hard Delete | Principle that governed SMS records are archived/inactivated rather than physically deleted. |

## 40. Annex C — Related Documents

- [Deployment Readiness Guide](deployment-readiness.md)
- [Backup and Restore Procedure](backup-and-restore.md)
- [Data Retention and Archive Policy](data-retention-and-archive-policy.md)
- [Permission Matrix](permission-matrix.md)
- [Electronic Approval Concept](electronic-approval-concept.md)
- [Production Logging / Request ID](production-logging-and-monitoring.md)
- [User Acceptance Test Pack](user-acceptance-test-pack.md)
- [Pilot Deployment Checklist](pilot-deployment-checklist.md)
- [Pilot Execution Support Pack](pilot-execution-support-pack.md)
- [Post-Pilot Feedback and Defect Register](post-pilot-feedback-and-defect-register.md)
- [Release Notes v1.0](release-notes-v1.0.md)
- [Version 1.0 Release Package Checklist](release-package-checklist.md)
