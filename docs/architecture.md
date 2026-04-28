# Architecture

## Overview

The planned system uses a modular monolith architecture with a FastAPI backend, React TypeScript frontend, and PostgreSQL database. The monolith should be organized into clear functional modules so the system remains simple to deploy while preserving strong boundaries between domains.

No application code is created in this documentation baseline.

## Planned Stack

- Backend: FastAPI
- Frontend: React TypeScript
- Database: PostgreSQL
- Reporting: server-side DOCX generation
- Authentication and authorization: role-based access control
- AI assistance: LLM integration for advisory risk structuring

## Repository Structure

```text
backend/
frontend/
docs/
docs/codex_tasks/
```

The `backend/` directory will contain the FastAPI application in future tasks.

The `frontend/` directory will contain the React TypeScript application in future tasks.

The `docs/` directory contains product, architecture, workflow, and data model documentation.

The `docs/codex_tasks/` directory contains implementation task records for future Codex work.

## Backend Modules

Future backend implementation should be divided into modules such as:

- identity and access control
- authority levels and boards
- risk records
- hazards, central events, causes, and consequences
- risk assessments
- mitigations and action tracking
- approvals and escalation
- monitoring and closure
- audit logging
- report generation
- LLM assistant orchestration

Modules should use explicit service boundaries even while deployed as one application.

## Frontend Areas

Future frontend implementation should support:

- risk list and filtering
- risk creation from Problem Description
- LLM-assisted structuring review
- bow-tie style risk structure views if appropriate
- initial and residual risk assessment forms
- mitigation and action tracking
- committee review screens
- approval and escalation screens
- monitoring and closure views
- audit history views
- report generation actions
- admin configuration for low-level boards and roles

## Database

PostgreSQL is the planned database. Important records should use stable identifiers, timestamps, status fields, and archive or deactivate fields instead of physical deletion.

Schema design should preserve historical meaning. For example, if a board is renamed later, existing records should still show the board context that applied when decisions were made.

## Role-Based Access Control

The system must enforce role-based access control on backend APIs and reflect permissions in the frontend. Frontend hiding of controls is not sufficient by itself.

Expected access patterns include:

- administrators manage users, roles, and configurable low-level boards
- risk creators create draft risks
- risk owners maintain assigned risks
- action owners update mitigation actions
- committee members review and approve within authority
- executives review and approve high-level escalations
- auditors review records and audit logs without changing controlled data

## Audit Logging

The backend must record a complete audit log for meaningful changes. Audit entries should capture:

- actor
- timestamp
- affected entity type
- affected entity identifier
- action
- previous value where appropriate
- new value where appropriate
- reason or comment where required by workflow
- request or correlation identifier where available

Audit logging should be treated as a cross-cutting requirement, not an optional feature inside individual screens.

## DOCX Reporting

DOCX reports should be generated from controlled database records. Reports should support committee review, approval evidence, mitigation status, risk assessments, and closure evidence.

Generated reports should either be reproducible from data or stored with metadata that links the report to the exact risk record version or generation timestamp.

## LLM Assistant Concept

The LLM assistant helps structure information from the Problem Description. It may suggest hazards, central events, causes, consequences, draft mitigations, and questions for clarification.

LLM output must be:

- advisory
- reviewable by authorized users
- editable before becoming controlled record data
- traceable in audit history when accepted or modified
- stored with enough metadata to understand what was suggested and what was adopted

The LLM must not approve risks, accept residual risk, bypass committees, or make final safety decisions.
