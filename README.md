# Aviation Risk Management Tool

A web-based aviation Safety Management System (SMS) Risk Management Tool for structured risk identification, assessment, mitigation, committee review, escalation, reporting, monitoring, closure, and audit logging.

The system manages a risk from the initial Problem Description through hazard identification, central event definition, causes, consequences, initial risk assessment, mitigation planning, residual risk assessment, approval, escalation, monitoring, closure, DOCX reporting, and a complete audit trail.

## Documentation

- [Product Vision](docs/product_vision.md)
- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [Data Model](docs/data_model.md)
- [Data Retention and Archive Policy](docs/data-retention-and-archive-policy.md)
- [Permission Matrix and Access Control Policy](docs/permission-matrix.md)
- [Electronic Approval / Signature Concept MVP](docs/electronic-approval-concept.md)
- [Production Logging and Error Monitoring Preparation](docs/production-logging-and-monitoring.md)
- [User Acceptance Test Pack](docs/user-acceptance-test-pack.md)
- [Pilot Deployment Checklist](docs/pilot-deployment-checklist.md)
- [Pilot Execution Support Pack](docs/pilot-execution-support-pack.md)
- [Operation Manual / User Guide](docs/operation-manual.md)
- [Release Notes v1.0](docs/release-notes-v1.0.md)
- [Version 1.0 Release Package Checklist](docs/release-package-checklist.md)
- [Codex Task 001](docs/codex_tasks/task_001_project_documentation.md)

## Planned Technology Baseline

- Backend: FastAPI
- Frontend: React with TypeScript
- Database: PostgreSQL
- Architecture: modular monolith
- Reporting: DOCX report generation
- AI assistance: LLM-assisted risk structuring from the Problem Description

## Frontend Local Startup

The React and TypeScript frontend expects the local backend API at
`http://127.0.0.1:8000` by default.

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend development server defaults to `http://127.0.0.1:5174`. The home
page checks backend connectivity through `GET /health`.

## Deployment Readiness

Before deployment, confirm CI is green, Production Configuration passes backend
startup safety validation, and secrets are configured outside the repository.
See the [Deployment Readiness Guide](docs/deployment-readiness.md) for
Environment Hardening, CORS Allowed Origins, JWT Secret, Evidence Storage, and
Generated Reports checklists.

## User Acceptance Testing

Complete the [User Acceptance Test Pack](docs/user-acceptance-test-pack.md) before pilot use. CI should be green before UAT begins, and a backup should be taken before UAT if persistent data is used.

Tracking templates:

- [UAT test matrix CSV](docs/templates/uat-test-matrix.csv)
- [UAT defect log CSV](docs/templates/uat-defect-log.csv)

## Pilot Deployment

Use the [Pilot Deployment Checklist](docs/pilot-deployment-checklist.md) for controlled pilot release readiness before limited operational use. This is not production deployment automation; it is a controlled checklist for pilot release readiness.

Pilot templates:

- [Pilot deployment checklist CSV](docs/templates/pilot-deployment-checklist.csv)
- [Pilot Go / No-Go decision CSV](docs/templates/pilot-go-no-go-decision.csv)
- [Pilot rollback log CSV](docs/templates/pilot-rollback-log.csv)

## Pilot Execution Support

Use the [Pilot Execution Support Pack](docs/pilot-execution-support-pack.md) to brief pilot users, schedule controlled pilot sessions, capture Pilot Feedback, maintain the Defect Register, review the daily log, and support Go / No-Go closeout decisions.

Pilot execution templates:

- [Pilot feedback form CSV](docs/templates/pilot-feedback-form.csv)
- [Pilot defect register CSV](docs/templates/pilot-defect-register.csv)
- [Pilot daily log CSV](docs/templates/pilot-daily-log.csv)

## Operation Manual / User Guide

See the [Operation Manual / User Guide](docs/operation-manual.md) for normal operation, features, procedures, limitations, and governance references. The manual is draft until reviewed by SMS/Quality/IT/governance stakeholders.

## Release Package

See the [Release Notes v1.0](docs/release-notes-v1.0.md), [Version 1.0 Release Package Checklist](docs/release-package-checklist.md), and [release package checklist CSV](docs/templates/release-package-checklist.csv) for pilot release package review. `v1.0.0-pilot` is the proposed pilot release tag and should only be created after final review.

Current pilot release candidate: `v1.0.0-pilot`.

## Backup and Restore

See the [Backup and Restore Procedure](docs/backup-and-restore.md) for local
Database Backup, Evidence Backup, Generated Reports Backup, and Restore
Procedure guidance. Helper scripts are under `scripts/`. The `backups/` folder
is ignored except for `.gitkeep`; do not commit backup outputs.

## Data Retention and Archive Policy

See the [Data Retention and Archive Policy](docs/data-retention-and-archive-policy.md) for MVP Data Retention, Archive Policy, No Hard Delete, Audit Integrity, and Evidence Preservation guidance. Governed SMS records should be archived, not hard-deleted; audit integrity and evidence traceability must be preserved.

## Permission Matrix and Access Control Policy

See the [Permission Matrix and Access Control Policy](docs/permission-matrix.md) for MVP Access Control expectations across Authority Level, Board of Origin, Fixed Governance Committee oversight, exports, archive/restore, and admin governance.

## Authority Structure

The tool supports three authority levels:

1. Low Level: Operational Boards
2. Middle Level: Risk Management Committee
3. High Level: Executive Safety Management Committee

Default low-level boards are:

- Flight Test Safety Committee - Operation
- Aircraft Safety Committee - Engineering Board
- Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE

Low-level boards are configurable by admin users. The middle and high-level committees are fixed and must not be deleted.

## Core Principles

- Role-based access control governs user actions and workflow transitions.
- Important records are not physically deleted; use archive, deactivate, or closure states.
- All meaningful changes must be captured in an audit log.
- Reports must be generated from controlled system data, not manually reconstructed.
- LLM output is advisory and must remain reviewable, editable, and auditable by authorized users.
