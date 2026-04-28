# Product Vision

## Purpose

The Aviation Risk Management Tool is a web-based system for managing aviation SMS risk records in a structured, auditable, and committee-driven process. It is intended to help safety, engineering, operations, manufacturing, quality, supply chain, and executive stakeholders manage risk consistently from first identification through closure.

The product should reduce fragmented spreadsheet-based tracking, improve traceability of risk decisions, standardize committee review, and support defensible audit evidence for aviation SMS governance.

## Scope

The tool manages the full lifecycle of an aviation risk record:

- Problem Description capture
- LLM-assisted risk structuring
- hazard identification
- central event definition
- cause and consequence analysis
- initial risk assessment
- mitigation planning and assignment
- residual risk assessment
- authority review and approval
- escalation between authority levels
- monitoring and periodic review
- closure decision
- DOCX report generation
- complete audit logging

## Users

Expected user groups include:

- operational board members
- risk owners
- action owners
- safety specialists
- engineering specialists
- manufacturing, quality, supply chain, and OHSE stakeholders
- Risk Management Committee members
- Executive Safety Management Committee members
- administrators
- auditors and read-only reviewers

## Authority Levels

### Low Level: Operational Boards

Operational boards perform first-line risk review and decision making for risks within their authority. Default boards are:

- Flight Test Safety Committee - Operation
- Aircraft Safety Committee - Engineering Board
- Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE

Low-level boards are configurable. Admin users may create, archive, rename, activate, or deactivate low-level boards. Archived or inactive boards must remain historically visible for past records.

### Middle Level: Risk Management Committee

The Risk Management Committee is a fixed authority level. It cannot be deleted. It reviews risks escalated beyond low-level authority, risks requiring cross-functional decision making, and risks assigned by governance rules.

### High Level: Executive Safety Management Committee

The Executive Safety Management Committee is a fixed authority level. It cannot be deleted. It reviews risks requiring executive acceptance, strategic decisions, major resource commitments, or acceptance of high residual risk.

## Product Principles

- The system is the authoritative record for managed SMS risks.
- Every important decision must have an accountable person, timestamp, and rationale.
- No important records should be physically deleted.
- Workflow state must be clear and enforceable.
- Audit history must be complete enough to reconstruct what changed, when, by whom, and why.
- LLM assistance must accelerate structuring but must never replace accountable human review.

## Success Criteria

The product is successful when authorized users can create, structure, assess, mitigate, approve, monitor, report, and close SMS risks without relying on uncontrolled external files for the official record.
