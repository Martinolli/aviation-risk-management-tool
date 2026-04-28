# Aviation Risk Management Tool

A web-based aviation Safety Management System (SMS) Risk Management Tool for structured risk identification, assessment, mitigation, committee review, escalation, reporting, monitoring, closure, and audit logging.

The system manages a risk from the initial Problem Description through hazard identification, central event definition, causes, consequences, initial risk assessment, mitigation planning, residual risk assessment, approval, escalation, monitoring, closure, DOCX reporting, and a complete audit trail.

## Documentation

- [Product Vision](docs/product_vision.md)
- [Architecture](docs/architecture.md)
- [Workflow](docs/workflow.md)
- [Data Model](docs/data_model.md)
- [Codex Task 001](docs/codex_tasks/task_001_project_documentation.md)

## Planned Technology Baseline

- Backend: FastAPI
- Frontend: React with TypeScript
- Database: PostgreSQL
- Architecture: modular monolith
- Reporting: DOCX report generation
- AI assistance: LLM-assisted risk structuring from the Problem Description

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
