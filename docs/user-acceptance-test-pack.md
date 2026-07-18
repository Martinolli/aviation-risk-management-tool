# User Acceptance Test Pack

## Purpose

This User Acceptance Test Pack validates application readiness for pilot/internal operational use of the Aviation Risk Management Tool. It provides controlled manual User Acceptance Test scenarios for Pilot Validation by pilot users, SMS users, committee members, administrators, and management users before controlled operational use.

The UAT Pack is designed to confirm workflow completeness, permission behavior, SMS governance controls, Audit integrity, reporting readiness, and operational readiness documentation. It does not introduce new business workflows, automated browser tooling, production data, or external test tools.

Completion of UAT feeds into the [Pilot Deployment Checklist](pilot-deployment-checklist.md). Critical and major defects must be reviewed before Go / No-Go.

## Scope

This UAT Pack covers:

- Login and session
- Dashboards
- Risk record creation
- Risk package completion
- Initial risk assessment
- Submission
- Committee decisions
- Mitigation actions
- Residual risk assessment
- Monitoring reviews
- Evidence management
- Reports and exports
- Audit trail
- Notifications
- Management dashboard
- Admin governance
- Permission matrix
- Data retention policy
- Electronic approvals
- Backup/restore documentation
- Logging/readiness diagnostics

## UAT Roles

- System Administrator: validates admin governance, user setup, membership assignment, fixed committee protection, readiness diagnostics, and operational documentation.
- SMS / Risk Owner: validates risk creation, risk package completion, initial assessment, submission, evidence, reports, exports, and audit traceability.
- LOW Authority Level committee member: validates LOW Authority Level decision workflow and confirms lower-level committee permissions.
- MIDDLE Authority Level Risk Management Committee member: validates MIDDLE Authority Level review, escalation, acceptance, and queue visibility.
- HIGH Authority Level Executive Safety Management Committee member: validates HIGH Authority Level review, executive acceptance, and Authority Level governance.
- Action Owner: validates mitigation action assignment, completion, queue visibility, and evidence references.
- Monitoring Owner: validates monitoring review assignment, completion, queue visibility, and review audit trail.
- Read-only / unauthorized comparison user if available: validates restricted access, authorization boundaries, and fail-closed behavior.

## Test Environment Prerequisites

- Backend running.
- Frontend running.
- PostgreSQL running.
- Alembic migrated.
- Admin user bootstrapped.
- Risk matrix seeded.
- Test access profiles seeded.
- Browser access confirmed.
- CI green before UAT.
- Backup taken before UAT if using persistent pilot data.

## UAT Execution Rules

- Record tester name.
- Record date/time.
- Record browser.
- Record test user.
- Record pass/fail.
- Record actual result.
- Record defect reference if failed.
- Do not use real sensitive investigation data unless approved.
- Do not upload classified/export-controlled evidence during UAT.

## UAT Scenario Matrix

| UAT ID | Area | Scenario | Primary Role | Expected Result | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| UAT-001 | Login and session | Login and Current User | SMS / Risk Owner | User signs in and the current user context is displayed correctly. | Not Started |  |
| UAT-002 | Dashboards | Operational Dashboard Loads | SMS / Risk Owner | Operational dashboard loads authorized operational data only. | Not Started |  |
| UAT-003 | Management dashboard | Management Dashboard Loads | Management user | Management dashboard loads authorized leadership summary data. | Not Started |  |
| UAT-004 | Risk creation | Create Risk Record | SMS / Risk Owner | Risk record is created in DRAFT and audit trail records creation. | Not Started |  |
| UAT-005 | Risk package | Complete Risk Package | SMS / Risk Owner | Required risk package fields are completed and saved. | Not Started |  |
| UAT-006 | Initial assessment | Create Initial Risk Assessment | SMS / Risk Owner | Initial risk assessment is calculated and saved. | Not Started |  |
| UAT-007 | Submission | Submit Risk to Board of Origin | SMS / Risk Owner | Complete risk is submitted to the correct Board of Origin. | Not Started |  |
| UAT-008 | Committee decision | LOW Authority Level Committee Decision | LOW Authority Level committee member | LOW Authority Level member records an allowed decision. | Not Started |  |
| UAT-009 | Escalation | Escalate to MIDDLE Authority Level | LOW Authority Level committee member | Risk escalates to MIDDLE Authority Level with audit traceability. | Not Started |  |
| UAT-010 | Committee decision | MIDDLE Authority Level Committee Decision | MIDDLE Authority Level Risk Management Committee member | MIDDLE Authority Level member records an allowed decision. | Not Started |  |
| UAT-011 | Escalation | Escalate to HIGH Authority Level | MIDDLE Authority Level Risk Management Committee member | Risk escalates to HIGH Authority Level with audit traceability. | Not Started |  |
| UAT-012 | Committee decision | HIGH Authority Level Acceptance | HIGH Authority Level Executive Safety Management Committee member | HIGH Authority Level acceptance is recorded and visible. | Not Started |  |
| UAT-013 | Mitigation actions | Create Mitigation Action | SMS / Risk Owner | Mitigation action is created with owner and due date. | Not Started |  |
| UAT-014 | Mitigation actions | Complete Mitigation Action | Action Owner | Mitigation action is completed and audit trail records completion. | Not Started |  |
| UAT-015 | Residual assessment | Create Residual Risk Assessment | SMS / Risk Owner | Residual risk assessment is saved after mitigation review. | Not Started |  |
| UAT-016 | Monitoring reviews | Create Monitoring Review | Monitoring Owner | Monitoring review is created with review date and owner. | Not Started |  |
| UAT-017 | Monitoring reviews | Complete Monitoring Review | Monitoring Owner | Monitoring review is completed and tracked. | Not Started |  |
| UAT-018 | Evidence management | Upload Evidence | SMS / Risk Owner | Evidence metadata/file is uploaded and linked to risk. | Not Started |  |
| UAT-019 | Evidence management | Archive Evidence if available | SMS / Risk Owner | Evidence archive action is available only where supported and is audited. | Not Started |  |
| UAT-020 | Reports | Generate Risk Dossier Report | SMS / Risk Owner | Risk dossier report generation completes. | Not Started |  |
| UAT-021 | Reports | Download Risk Dossier Report | SMS / Risk Owner | Generated dossier downloads successfully. | Not Started |  |
| UAT-022 | Committee packs | Generate Committee Meeting Pack | Committee member | Committee meeting pack is generated from controlled data. | Not Started |  |
| UAT-023 | Committee meetings | Create Committee Meeting | Committee member | Committee meeting is created for the correct committee. | Not Started |  |
| UAT-024 | Committee minutes | Finalize Committee Minutes | Committee member | Final minutes are locked/finalized according to workflow. | Not Started |  |
| UAT-025 | Evidence package | Export Risk Evidence Package | SMS / Risk Owner | Authorized evidence package export downloads. | Not Started |  |
| UAT-026 | Risk register export | Export Risk Register CSV | SMS / Risk Owner | Authorized risk register CSV downloads with filters applied. | Not Started |  |
| UAT-027 | Risk register export | Export Risk Register DOCX | SMS / Risk Owner | Authorized risk register DOCX downloads with filters applied. | Not Started |  |
| UAT-028 | Audit export | Export Audit Trail CSV/DOCX | System Administrator | Authorized audit export downloads in requested format. | Not Started |  |
| UAT-029 | Notifications | View Notifications | Any assigned user | User sees only authorized notifications. | Not Started |  |
| UAT-030 | Audit trail | View Audit Trail | System Administrator | Audit trail displays relevant events without unauthorized exposure. | Not Started |  |
| UAT-031 | Permission matrix | View Permission Matrix | System Administrator | Permission matrix documentation is available for review. | Not Started |  |
| UAT-032 | Data retention | View Data Retention Policy | System Administrator | Data retention policy documentation is available for review. | Not Started |  |
| UAT-033 | Electronic approvals | Create Electronic Approval | Authorized approver | Electronic approval is recorded with audit traceability. | Not Started |  |
| UAT-034 | Electronic approvals | Duplicate Electronic Approval Rejected | Authorized approver | Duplicate approval attempt is rejected. | Not Started |  |
| UAT-035 | Permissions | Unauthorized User Cannot Access Restricted Risk | Read-only / unauthorized comparison user if available | Restricted risk access is denied. | Not Started |  |
| UAT-036 | Permissions | Lower Authority User Cannot Decide Higher Authority Risk | LOW Authority Level committee member | Lower Authority Level user cannot decide higher Authority Level risk. | Not Started |  |
| UAT-037 | Admin governance | Admin Governance - Create User | System Administrator | Admin creates a user account using governed admin workflow. | Not Started |  |
| UAT-038 | Admin governance | Admin Governance - Assign Membership | System Administrator | Admin assigns committee or role membership. | Not Started |  |
| UAT-039 | Admin governance | Admin Governance - Fixed Committees Protected | System Administrator | Fixed committees cannot be deleted or improperly modified. | Not Started |  |
| UAT-040 | Health/readiness | Health and Readiness Endpoints | System Administrator | Health and readiness endpoints respond without exposing secrets. | Not Started |  |
| UAT-041 | Backup/restore | Backup Procedure Documented | System Administrator | Backup/restore procedure is available and understood. | Not Started |  |
| UAT-042 | Logging/readiness | Logging Request ID Check | System Administrator | Request ID is available for operational diagnostics. | Not Started |  |
| UAT-043 | Search/filtering | Risk Search and Filtering | SMS / Risk Owner | Search/filtering returns authorized matching records only. | Not Started |  |
| UAT-044 | Decision queue | My Decision Queue | Committee member | Decision queue shows assigned authorized decisions. | Not Started |  |
| UAT-045 | Actions queue | My Actions Queue | Action Owner | Actions queue shows assigned mitigation actions. | Not Started |  |
| UAT-046 | Monitoring queue | My Monitoring Queue | Monitoring Owner | Monitoring queue shows assigned monitoring reviews. | Not Started |  |

Status values:

- Not Started
- Pass
- Fail
- Blocked
- Observation

## Detailed Test Cases

### UAT-001 - Login and Current User

Objective:
Confirm an authorized user can sign in and verify their current user context.

Role / Test User:
SMS / Risk Owner

Preconditions:

- Backend and frontend are running.
- Test user exists and has valid credentials.

Steps:

1. Open the frontend application.
2. Enter the test user's email and password.
3. Submit the login form.
4. Open the current user or profile area if available.
5. Confirm the displayed user identity, role, and Authority Level.

Expected Result:

- Login succeeds.
- Session remains active after navigation.
- Current user details match the test profile.
- Unauthorized session errors are not shown.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-002 - Operational Dashboard Loads

Objective:
Confirm the operational dashboard loads for an authorized operational user.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- User has access to operational dashboard data.

Steps:

1. Open the operational dashboard.
2. Confirm summary counts and queues load.
3. Select visible dashboard links or drill-ins if available.
4. Confirm returned records remain within the user's authorized scope.

Expected Result:

- Dashboard loads without an application error.
- Counts and lists are visible where data exists.
- Empty states are understandable where no data exists.
- Unauthorized records are not displayed.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-003 - Management Dashboard Loads

Objective:
Confirm a management user can view the management dashboard.

Role / Test User:
Management user

Preconditions:

- Management test user is logged in.
- Management dashboard access is enabled for the user.

Steps:

1. Open the management dashboard.
2. Confirm executive summary panels load.
3. Review decision queues, notifications, and risk summaries.
4. Confirm visible records are within the user's authorized management scope.

Expected Result:

- Management dashboard loads successfully.
- Leadership metrics and queues display correctly.
- Unauthorized records are excluded.
- Page failures are handled with clear messaging.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-004 - Create Risk Record

Objective:
Confirm an authenticated SMS/risk user can create a new risk record.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- User has access to Risk Records page.

Steps:

1. Open Risk Records.
2. Select Create Risk.
3. Enter Problem Description.
4. Select Domain.
5. Select or confirm Board of Origin if required.
6. Save the record.

Expected Result:

- Risk record is created.
- Risk ID is assigned.
- Workflow Status is DRAFT.
- Lifecycle Status is OPEN.
- Audit trail records creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-005 - Complete Risk Package

Objective:
Confirm a risk owner can complete the required risk package details.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- A DRAFT risk record exists and is accessible.

Steps:

1. Open the DRAFT risk record.
2. Complete hazard, central event, causes, and consequences as applicable.
3. Review required package readiness items.
4. Save changes.
5. Reopen the risk record.

Expected Result:

- Risk package fields are saved.
- Required readiness indicators update.
- Original Problem Description remains available.
- Audit trail records updates.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-006 - Create Initial Risk Assessment

Objective:
Confirm an initial risk assessment can be created and saved.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk package has sufficient assessment inputs.
- Risk matrix is seeded.

Steps:

1. Open the risk record.
2. Open the initial risk assessment area.
3. Select probability and severity values.
4. Review the calculated risk level.
5. Save the assessment.

Expected Result:

- Initial risk assessment is saved.
- Risk level is calculated from the seeded risk matrix.
- Assessment is visible after refresh.
- Audit trail records assessment creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-007 - Submit Risk to Board of Origin

Objective:
Confirm a complete risk can be submitted to the correct Board of Origin.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk package and initial risk assessment are complete.
- Board of Origin is assigned.

Steps:

1. Open the complete risk record.
2. Review submission readiness indicators.
3. Select Submit.
4. Confirm the submission action.
5. Review workflow status and Board of Origin routing.

Expected Result:

- Submission succeeds only when readiness is complete.
- Risk routes to the Board of Origin.
- Workflow status changes from DRAFT to submitted/in review state.
- Audit trail records submission.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-008 - LOW Authority Level Committee Decision

Objective:
Confirm a LOW Authority Level committee member can record an allowed committee decision.

Role / Test User:
LOW Authority Level committee member

Preconditions:

- LOW Authority Level member is logged in.
- Submitted risk is assigned to the user's committee or Board of Origin.

Steps:

1. Open the assigned risk or decision queue.
2. Review submitted risk details.
3. Select an allowed LOW Authority Level decision.
4. Enter decision rationale.
5. Submit the decision.

Expected Result:

- Allowed decision is saved.
- Decision rationale is visible.
- Workflow state updates according to the decision.
- Audit integrity is preserved through an audit entry.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-009 - Escalate to MIDDLE Authority Level

Objective:
Confirm a risk can be escalated from LOW Authority Level to MIDDLE Authority Level.

Role / Test User:
LOW Authority Level committee member

Preconditions:

- LOW Authority Level member is logged in.
- Risk is under LOW Authority Level review.

Steps:

1. Open the risk decision view.
2. Select an escalation decision to MIDDLE Authority Level.
3. Enter escalation rationale.
4. Submit the decision.
5. Confirm the risk appears in the appropriate MIDDLE Authority Level queue.

Expected Result:

- Escalation is accepted.
- Risk Authority Level moves to MIDDLE Authority Level review as applicable.
- MIDDLE Authority Level committee users can see the item.
- Audit trail records escalation and rationale.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-010 - MIDDLE Authority Level Committee Decision

Objective:
Confirm a MIDDLE Authority Level Risk Management Committee member can record an allowed decision.

Role / Test User:
MIDDLE Authority Level Risk Management Committee member

Preconditions:

- MIDDLE Authority Level member is logged in.
- Risk is assigned to MIDDLE Authority Level review.

Steps:

1. Open My Decision Queue.
2. Select the escalated risk.
3. Review the LOW Authority Level decision history.
4. Record an allowed MIDDLE Authority Level decision and rationale.
5. Submit the decision.

Expected Result:

- MIDDLE Authority Level decision is saved.
- Prior LOW Authority Level decision remains visible.
- Workflow state updates correctly.
- Audit trail records the decision.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-011 - Escalate to HIGH Authority Level

Objective:
Confirm a risk can be escalated from MIDDLE Authority Level to HIGH Authority Level.

Role / Test User:
MIDDLE Authority Level Risk Management Committee member

Preconditions:

- MIDDLE Authority Level member is logged in.
- Risk is under MIDDLE Authority Level review.

Steps:

1. Open the MIDDLE Authority Level decision view.
2. Select escalation to HIGH Authority Level.
3. Enter escalation rationale.
4. Submit the decision.
5. Confirm the risk is visible to HIGH Authority Level users.

Expected Result:

- Escalation is saved.
- Risk is routed to HIGH Authority Level review.
- Executive committee users can access the decision item.
- Audit trail records escalation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-012 - HIGH Authority Level Acceptance

Objective:
Confirm a HIGH Authority Level Executive Safety Management Committee member can accept a risk where allowed.

Role / Test User:
HIGH Authority Level Executive Safety Management Committee member

Preconditions:

- HIGH Authority Level member is logged in.
- Risk is routed to HIGH Authority Level review.

Steps:

1. Open the HIGH Authority Level decision queue.
2. Select the risk.
3. Review risk package, assessment, mitigation, and prior decisions.
4. Select acceptance if appropriate for the test case.
5. Enter rationale and submit.

Expected Result:

- HIGH Authority Level acceptance is recorded.
- Decision details and rationale are visible.
- Workflow status updates according to the decision.
- Audit trail records the executive acceptance.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-013 - Create Mitigation Action

Objective:
Confirm a mitigation action can be created and assigned.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk record exists and is accessible.
- Action Owner test user exists.

Steps:

1. Open the risk record.
2. Open mitigation actions.
3. Select Create Action.
4. Enter action description, owner, due date, and status.
5. Save the action.

Expected Result:

- Mitigation action is created.
- Action Owner is assigned.
- Due date and description are visible.
- Audit trail records action creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-014 - Complete Mitigation Action

Objective:
Confirm an Action Owner can complete an assigned mitigation action.

Role / Test User:
Action Owner

Preconditions:

- Action Owner is logged in.
- Assigned open mitigation action exists.

Steps:

1. Open My Actions Queue.
2. Select the assigned action.
3. Enter completion notes or evidence reference if required.
4. Mark the action complete.
5. Save the update.

Expected Result:

- Mitigation action status changes to complete.
- Completion notes are visible.
- Risk mitigation progress updates where applicable.
- Audit trail records completion.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-015 - Create Residual Risk Assessment

Objective:
Confirm a residual risk assessment can be created after mitigation review.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Initial assessment exists.
- Mitigation actions have been reviewed or completed as required.

Steps:

1. Open the risk record.
2. Open residual risk assessment.
3. Select residual probability and severity values.
4. Review the calculated residual risk level.
5. Save the residual assessment.

Expected Result:

- Residual risk assessment is saved.
- Residual risk level is calculated correctly.
- Residual assessment is visible after refresh.
- Audit trail records residual assessment creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-016 - Create Monitoring Review

Objective:
Confirm a monitoring review can be created and assigned.

Role / Test User:
Monitoring Owner

Preconditions:

- Monitoring Owner exists.
- Risk record is accessible and eligible for monitoring.

Steps:

1. Open the risk record.
2. Open monitoring reviews.
3. Select Create Monitoring Review.
4. Enter review owner, due date, and monitoring objective.
5. Save the review.

Expected Result:

- Monitoring review is created.
- Monitoring Owner is assigned.
- Review due date and objective are visible.
- Audit trail records review creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-017 - Complete Monitoring Review

Objective:
Confirm a Monitoring Owner can complete an assigned monitoring review.

Role / Test User:
Monitoring Owner

Preconditions:

- Monitoring Owner is logged in.
- Assigned open monitoring review exists.

Steps:

1. Open My Monitoring Queue.
2. Select the assigned monitoring review.
3. Enter review outcome and notes.
4. Mark the monitoring review complete.
5. Save the update.

Expected Result:

- Monitoring review status changes to complete.
- Outcome and notes are visible.
- Related risk monitoring status updates where applicable.
- Audit trail records completion.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-018 - Upload Evidence

Objective:
Confirm an authorized user can upload evidence to a risk record.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk record is accessible.
- Approved non-sensitive UAT evidence file is available.

Steps:

1. Open the risk record.
2. Open evidence management.
3. Select Upload Evidence.
4. Choose an approved UAT evidence file.
5. Enter evidence description and save.

Expected Result:

- Evidence upload succeeds.
- Evidence is linked to the risk record.
- Evidence metadata is visible.
- Audit trail records evidence upload.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-019 - Archive Evidence if available

Objective:
Confirm evidence archive behavior is controlled and audited if the action is available.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk record has uploaded evidence.
- Evidence archive action is available in the tested build.

Steps:

1. Open the evidence list for the risk record.
2. Select an evidence item.
3. Choose archive or equivalent action if available.
4. Confirm the action.
5. Review the evidence list and audit trail.

Expected Result:

- If available, archive action changes the evidence state without hard delete.
- If unavailable, the UI clearly does not offer the action.
- Evidence traceability remains intact.
- Audit trail records archive action when performed.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-020 - Generate Risk Dossier Report

Objective:
Confirm an authorized user can generate a risk dossier report.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk record has sufficient data for report generation.

Steps:

1. Open the risk record.
2. Select Generate Risk Dossier Report.
3. Wait for report generation to complete.
4. Review report generation status.
5. Confirm generated report metadata is visible if provided.

Expected Result:

- Report generation completes without error.
- Generated report is linked to the correct risk.
- Report metadata is available where supported.
- Audit trail records report generation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-021 - Download Risk Dossier Report

Objective:
Confirm an authorized user can download a generated risk dossier report.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Generated risk dossier report exists.

Steps:

1. Open generated reports or the related risk record.
2. Select the generated dossier report.
3. Download the report.
4. Open the downloaded file.
5. Confirm it refers to the correct risk.

Expected Result:

- Report downloads successfully.
- File opens locally.
- Report content matches the selected risk.
- Unauthorized report data is not included.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-022 - Generate Committee Meeting Pack

Objective:
Confirm a committee meeting pack can be generated from controlled system data.

Role / Test User:
Committee member

Preconditions:

- Committee member is logged in.
- Committee meeting or eligible risk set exists.

Steps:

1. Open committee meetings or committee pack area.
2. Select the relevant committee meeting or risk set.
3. Generate the committee meeting pack.
4. Download or open the generated pack.
5. Review included risks and decisions.

Expected Result:

- Committee meeting pack generation completes.
- Pack includes authorized committee data.
- Pack does not include unauthorized risks.
- Audit trail records pack generation where applicable.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-023 - Create Committee Meeting

Objective:
Confirm an authorized committee user can create a committee meeting.

Role / Test User:
Committee member

Preconditions:

- Committee member is logged in.
- User has access to the relevant committee.

Steps:

1. Open committee meetings.
2. Select Create Meeting.
3. Enter meeting title, committee, date/time, and agenda details.
4. Save the meeting.
5. Reopen the meeting record.

Expected Result:

- Committee meeting is created.
- Meeting appears under the correct committee.
- Meeting details are retained after refresh.
- Audit trail records meeting creation.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-024 - Finalize Committee Minutes

Objective:
Confirm committee minutes can be finalized according to the meeting workflow.

Role / Test User:
Committee member

Preconditions:

- Committee member is logged in.
- Committee meeting exists with draft minutes.

Steps:

1. Open the committee meeting.
2. Review draft minutes.
3. Add final comments or corrections.
4. Select Finalize Minutes.
5. Confirm finalization.

Expected Result:

- Minutes are finalized.
- Finalized minutes are available for review or download.
- Further edits are restricted according to workflow.
- Audit trail records finalization.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-025 - Export Risk Evidence Package

Objective:
Confirm an authorized user can export a controlled evidence package for a risk.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Risk record has evidence and generated/linked data.

Steps:

1. Open the risk record.
2. Select Export Risk Evidence Package.
3. Confirm export generation.
4. Download the exported package.
5. Review package contents at a high level.

Expected Result:

- Evidence package export downloads successfully.
- Package includes authorized risk evidence and related controlled artifacts.
- Package excludes unauthorized data.
- Audit trail records export.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-026 - Export Risk Register CSV

Objective:
Confirm an authorized user can export the risk register as CSV.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- User has access to Risk Records or export controls.

Steps:

1. Open Risk Records.
2. Apply a known filter if desired.
3. Select Export CSV.
4. Open the downloaded CSV.
5. Compare rows against the authorized filtered list.

Expected Result:

- CSV downloads successfully.
- CSV includes only authorized records.
- Applied filters are reflected in export content.
- Audit trail records export where applicable.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-027 - Export Risk Register DOCX

Objective:
Confirm an authorized user can export the risk register as DOCX.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- User has access to Risk Records or export controls.

Steps:

1. Open Risk Records.
2. Apply a known filter if desired.
3. Select Export DOCX.
4. Open the downloaded DOCX.
5. Compare records against the authorized filtered list.

Expected Result:

- DOCX downloads successfully.
- DOCX includes only authorized records.
- Applied filters are reflected in export content.
- Document opens without corruption.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-028 - Export Audit Trail CSV/DOCX

Objective:
Confirm an authorized user can export the Audit Trail in CSV and DOCX where available.

Role / Test User:
System Administrator

Preconditions:

- System Administrator is logged in.
- Audit events exist.

Steps:

1. Open the Audit Trail or audit export area.
2. Apply a known date, actor, entity, or action filter if available.
3. Export CSV.
4. Export DOCX where available.
5. Review exported content.

Expected Result:

- Audit Trail export downloads in the selected format.
- Export content matches applied filters.
- Sensitive secrets are not exposed.
- Audit integrity and traceability are preserved.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-029 - View Notifications

Objective:
Confirm a user can view relevant notifications.

Role / Test User:
Any assigned user

Preconditions:

- User is logged in.
- User has assigned decisions, actions, monitoring reviews, or other notification-worthy items.

Steps:

1. Open notifications.
2. Review notification list.
3. Select a notification.
4. Confirm it opens the related item where supported.
5. Confirm unrelated notifications are absent.

Expected Result:

- Notifications load successfully.
- Notifications are relevant to the user.
- Links navigate to authorized records only.
- Empty state is clear if no notifications exist.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-030 - View Audit Trail

Objective:
Confirm an authorized user can view the Audit Trail.

Role / Test User:
System Administrator

Preconditions:

- System Administrator is logged in.
- Audit events exist from prior UAT actions.

Steps:

1. Open the Audit Trail.
2. Search or filter for a known UAT action.
3. Open or inspect the audit entry.
4. Confirm actor, action, entity, and timestamp are present.
5. Confirm no sensitive secrets are displayed.

Expected Result:

- Audit Trail loads successfully.
- Known UAT actions are visible.
- Audit integrity is maintained with actor and timestamp details.
- Secret values are not exposed.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-031 - View Permission Matrix

Objective:
Confirm the permission matrix is available for governance review.

Role / Test User:
System Administrator

Preconditions:

- User has access to project documentation or admin guidance.

Steps:

1. Open the README documentation links.
2. Select Permission Matrix and Access Control Policy.
3. Review Authority Level and Board of Origin rules.
4. Confirm export, archive, approval, and admin governance expectations are documented.

Expected Result:

- Permission matrix documentation opens.
- Authority Level rules are clear.
- Authorization boundaries are documented.
- Governance review can proceed from the document.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-032 - View Data Retention Policy

Objective:
Confirm the data retention policy is available for governance review.

Role / Test User:
System Administrator

Preconditions:

- User has access to project documentation or admin guidance.

Steps:

1. Open the README documentation links.
2. Select Data Retention and Archive Policy.
3. Review retention, archive, legal hold, and no hard delete expectations.
4. Confirm evidence and audit retention expectations are documented.

Expected Result:

- Data retention policy opens.
- Archive and no hard delete expectations are clear.
- Audit integrity and evidence preservation are documented.
- Governance review can proceed from the document.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-033 - Create Electronic Approval

Objective:
Confirm an authorized approver can create an electronic approval.

Role / Test User:
Authorized approver

Preconditions:

- Authorized approver is logged in.
- Approvable record or decision exists.
- Electronic approval concept has been reviewed.

Steps:

1. Open the record requiring approval.
2. Select the electronic approval action.
3. Review acknowledgement wording.
4. Submit the approval.
5. Review approval reference and audit trail.

Expected Result:

- Electronic approval is recorded.
- Approval includes actor, timestamp, record reference, and acknowledgement context.
- Signature / Electronic Approval Reference is available where supported.
- Audit trail records approval.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-034 - Duplicate Electronic Approval Rejected

Objective:
Confirm duplicate electronic approval attempts are rejected.

Role / Test User:
Authorized approver

Preconditions:

- Authorized approver is logged in.
- The approver has already approved the same record/action.

Steps:

1. Open the previously approved record.
2. Attempt to submit the same electronic approval again.
3. Review the validation message.
4. Check whether any duplicate approval is created.
5. Review audit trail behavior.

Expected Result:

- Duplicate approval attempt is rejected.
- Clear validation message is displayed.
- No duplicate approval record is created.
- Audit integrity is preserved.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-035 - Unauthorized User Cannot Access Restricted Risk

Objective:
Confirm an unauthorized or read-only comparison user cannot access a restricted risk.

Role / Test User:
Read-only / unauthorized comparison user if available

Preconditions:

- Restricted risk record exists.
- Unauthorized comparison user is logged in.
- Risk ID or link is known for the test.

Steps:

1. Attempt to open the restricted risk from direct URL if known.
2. Search for the restricted risk from Risk Records.
3. Try any available dashboard or export path that might reveal the risk.
4. Record the response for each attempt.

Expected Result:

- Restricted risk is not visible in lists, dashboards, queues, or exports.
- Direct access is denied.
- Error response or UI message does not expose sensitive risk details.
- Authorization fails closed.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-036 - Lower Authority User Cannot Decide Higher Authority Risk

Objective:
Confirm a lower Authority Level user cannot decide a higher Authority Level risk.

Role / Test User:
LOW Authority Level committee member

Preconditions:

- LOW Authority Level member is logged in.
- Higher Authority Level risk exists.

Steps:

1. Attempt to open the higher Authority Level risk decision view.
2. Attempt to submit a decision if controls are visible.
3. Review displayed permissions or validation message.
4. Confirm the higher Authority Level risk is not changed.

Expected Result:

- Lower Authority Level user cannot make the decision.
- Decision controls are hidden or submission is rejected.
- Risk workflow state remains unchanged.
- Audit trail does not show an unauthorized successful decision.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-037 - Admin Governance - Create User

Objective:
Confirm a System Administrator can create a governed user account.

Role / Test User:
System Administrator

Preconditions:

- System Administrator is logged in.
- New test user details are approved for UAT use.

Steps:

1. Open admin governance.
2. Select Create User.
3. Enter user email, display name, role, and Authority Level.
4. Save the user.
5. Confirm the user appears in the user list.

Expected Result:

- User account is created.
- User attributes are saved correctly.
- Admin action is audited.
- Created user can be used only according to assigned permissions.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-038 - Admin Governance - Assign Membership

Objective:
Confirm a System Administrator can assign committee or membership access.

Role / Test User:
System Administrator

Preconditions:

- System Administrator is logged in.
- Test user exists.
- Target committee or membership exists.

Steps:

1. Open admin governance.
2. Select the test user.
3. Assign the committee, Board of Origin, or membership role required by the test.
4. Save changes.
5. Log in as the test user or refresh their permissions if required.

Expected Result:

- Membership assignment is saved.
- User gains only the intended access.
- Admin action is audited.
- Unauthorized memberships are not assigned accidentally.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-039 - Admin Governance - Fixed Committees Protected

Objective:
Confirm fixed committees are protected from deletion or improper modification.

Role / Test User:
System Administrator

Preconditions:

- System Administrator is logged in.
- Fixed middle and high-level committees exist.

Steps:

1. Open admin committee governance.
2. Select a fixed committee.
3. Attempt to delete it or perform a restricted modification if controls are visible.
4. Review the validation response.
5. Confirm the committee remains available.

Expected Result:

- Fixed committees are protected.
- Delete or restricted modification is unavailable or rejected.
- Clear message is displayed where applicable.
- Audit trail records any attempted governed action if supported.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-040 - Health and Readiness Endpoints

Objective:
Confirm health and readiness endpoints support operational readiness checks without exposing secrets.

Role / Test User:
System Administrator

Preconditions:

- Backend is running.
- User has access to endpoint testing method approved for UAT.

Steps:

1. Open or request `GET /health`.
2. Open or request `GET /health/readiness`.
3. Confirm both endpoints respond.
4. Review readiness fields for safe operational metadata.
5. Confirm secrets are not exposed.

Expected Result:

- Health endpoint returns service availability.
- Readiness endpoint returns safe readiness diagnostics.
- JWT secrets, passwords, and database URLs are not exposed.
- Response supports production readiness review.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-041 - Backup Procedure Documented

Objective:
Confirm backup and restore procedure documentation is available before UAT or pilot use.

Role / Test User:
System Administrator

Preconditions:

- User has access to project documentation.
- Persistent pilot data use has been decided.

Steps:

1. Open the README documentation links.
2. Select Backup and Restore Procedure.
3. Review database, evidence, and generated reports backup scope.
4. Confirm restore guidance and verification expectations are documented.
5. If persistent pilot data is used, record backup reference before UAT.

Expected Result:

- Backup/restore documentation is available.
- Backup scope includes database, evidence uploads, and generated reports.
- Restore procedure and verification expectations are clear.
- Backup reference is recorded when persistent pilot data is used.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-042 - Logging Request ID Check

Objective:
Confirm Request ID correlation is available for production logging preparation.

Role / Test User:
System Administrator

Preconditions:

- Backend is running.
- Backend logs are accessible to authorized UAT operator.

Steps:

1. Perform a known UI action or API request.
2. Locate the related backend log entry.
3. Confirm a Request ID is present.
4. Confirm request completion details are present.
5. Confirm sensitive request data is not logged.

Expected Result:

- Request ID appears in response and/or logs where supported.
- Logs support operational diagnostics.
- Sensitive data is not logged.
- Logging behavior supports SMS governance review.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-043 - Risk Search and Filtering

Objective:
Confirm risk search and filtering return authorized matching records only.

Role / Test User:
SMS / Risk Owner

Preconditions:

- User is logged in.
- Multiple accessible and inaccessible risk records exist for comparison.

Steps:

1. Open Risk Records.
2. Search by a known keyword.
3. Apply status, Authority Level, Board of Origin, or date filters if available.
4. Review result count and listed records.
5. Export filtered results if included in UAT scope.

Expected Result:

- Search and filters return matching authorized records.
- Inaccessible records are excluded.
- Filter state is clear to the user.
- Exported records match the authorized filtered result set where tested.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-044 - My Decision Queue

Objective:
Confirm committee members can view their assigned decision queue.

Role / Test User:
Committee member

Preconditions:

- Committee member is logged in.
- At least one risk is pending the user's committee decision.

Steps:

1. Open My Decision Queue.
2. Review listed items.
3. Select a decision item.
4. Confirm it opens the correct risk or decision view.
5. Confirm unrelated decisions are absent.

Expected Result:

- My Decision Queue loads.
- Assigned authorized decision items are visible.
- Unassigned or unauthorized items are excluded.
- Links navigate to the correct record.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-045 - My Actions Queue

Objective:
Confirm an Action Owner can view assigned mitigation actions.

Role / Test User:
Action Owner

Preconditions:

- Action Owner is logged in.
- At least one mitigation action is assigned to the user.

Steps:

1. Open My Actions Queue.
2. Review assigned actions.
3. Select an action.
4. Confirm related risk context is visible if authorized.
5. Confirm unrelated actions are absent.

Expected Result:

- My Actions Queue loads.
- Assigned mitigation actions are visible.
- Unauthorized risk details are not exposed.
- Empty state is clear if no actions are assigned.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

### UAT-046 - My Monitoring Queue

Objective:
Confirm a Monitoring Owner can view assigned monitoring reviews.

Role / Test User:
Monitoring Owner

Preconditions:

- Monitoring Owner is logged in.
- At least one monitoring review is assigned to the user.

Steps:

1. Open My Monitoring Queue.
2. Review assigned monitoring reviews.
3. Select a monitoring review.
4. Confirm related risk context is visible if authorized.
5. Confirm unrelated monitoring reviews are absent.

Expected Result:

- My Monitoring Queue loads.
- Assigned monitoring reviews are visible.
- Unauthorized risk details are not exposed.
- Empty state is clear if no monitoring reviews are assigned.

Actual Result:
[To be completed during UAT]

Pass / Fail:
[To be completed during UAT]

Defect / Observation:
[To be completed during UAT]

Evidence / Screenshot Reference:
[To be completed during UAT]

## UAT Defect Log

| Defect ID | UAT ID | Date | Tester | Severity | Description | Expected Result | Actual Result | Screenshot / Evidence | Assigned To | Status | Resolution Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEF-001 |  |  |  |  |  |  |  |  |  |  |  |

Severity values:

- Critical
- Major
- Minor
- Observation

## UAT Sign-Off

| Field | Value |
| --- | --- |
| UAT Cycle | [To be completed during UAT] |
| Environment | [To be completed during UAT] |
| Version / Commit SHA | [To be completed during UAT] |
| Start Date | [To be completed during UAT] |
| End Date | [To be completed during UAT] |
| Total Tests | [To be completed during UAT] |
| Passed | [To be completed during UAT] |
| Failed | [To be completed during UAT] |
| Blocked | [To be completed during UAT] |
| Open Critical Defects | [To be completed during UAT] |
| Open Major Defects | [To be completed during UAT] |

Recommendation:

- Accept for pilot use
- Accept with limitations
- Re-test required
- Not accepted

| Name | Role | Authority Level | Signature / Electronic Approval Reference | Date | Comments |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

Final UAT sign-off should follow company SMS, Quality, IT/cybersecurity, and governance requirements.
