# Workflow

## Risk Lifecycle

The tool manages risks through a controlled lifecycle. Exact status names may be refined during implementation, but the baseline workflow is:

1. Draft
2. Structured
3. Initial Assessment
4. Mitigation Planning
5. Residual Assessment
6. Committee Review
7. Approved or Escalated
8. Monitoring
9. Closure Review
10. Closed or Archived

Important records should not be physically deleted. Records that should no longer be active must be closed, archived, or deactivated according to their type.

## Step Details

### 1. Problem Description

A user creates a risk record with a Problem Description. This is the starting point for risk structuring and must remain visible in the record history.

### 2. LLM-Assisted Structuring

The system may call an LLM to propose structured risk content from the Problem Description, including:

- hazards
- central event
- causes
- consequences
- possible mitigations
- clarification questions

The user must review and accept or edit any suggestion before it becomes controlled risk data.

### 3. Hazard and Central Event Definition

The risk is structured around one or more hazards and a defined central event. Causes and consequences are linked to the central event so reviewers can understand the risk scenario.

### 4. Initial Risk Assessment

Authorized users assess the initial risk before mitigations. The assessment should capture severity, likelihood or probability, risk level, rationale, assessor, and timestamp.

### 5. Mitigation Planning

Mitigations are defined to reduce risk. Each mitigation should have an owner, due date where applicable, status, and evidence or completion notes.

### 6. Residual Risk Assessment

After mitigations are proposed or implemented, authorized users assess residual risk. The residual assessment should capture the same core evidence as the initial assessment and explain how mitigations changed the risk.

### 7. Authority Review

Risks are reviewed by the authority level appropriate to their risk level, domain, and governance rules.

Low-level Operational Boards include:

- Flight Test Safety Committee - Operation
- Aircraft Safety Committee - Engineering Board
- Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE

The Risk Management Committee is the fixed middle level.

The Executive Safety Management Committee is the fixed high level.

### 8. Approval or Escalation

An authority may approve, reject, request rework, or escalate a risk. Escalation should preserve the lower-level decision history and rationale.

Middle and high-level authorities are fixed and cannot be deleted. Low-level boards are configurable but must remain historically traceable.

### 9. Monitoring

Approved risks may require monitoring. Monitoring should capture review dates, status updates, effectiveness checks, and any decision to reassess or escalate.

### 10. Closure

Closure requires an authorized decision and rationale. Closure should preserve the full record, including assessments, mitigations, approvals, reports, and audit history.

## Audit Requirements

Every meaningful workflow transition and data change must be auditable. Examples include:

- risk creation
- LLM suggestion acceptance or modification
- hazard, cause, consequence, and mitigation changes
- initial and residual assessment changes
- ownership changes
- board assignment changes
- approval, rejection, rework, and escalation decisions
- monitoring updates
- closure decisions
- archive, deactivate, and reactivate actions

## Report Requirements

The system must generate DOCX reports for controlled risk records. Reports should include enough information to support committee review, approval evidence, and audit needs.

Expected report content includes:

- risk identifier and title
- Problem Description
- hazards and central event
- causes and consequences
- initial risk assessment
- mitigations and action status
- residual risk assessment
- authority reviews and decisions
- monitoring and closure information
- generated timestamp and report metadata
