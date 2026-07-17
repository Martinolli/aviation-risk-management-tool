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
