# Task 001 - Project Documentation Baseline

## Objective

Create the initial documentation and folder structure for an aviation SMS Risk Management Tool.

## Context

This system is a web-based Risk Management Tool for aviation Safety Management System environments. It manages risks from an initial Problem Description through hazard identification, central event definition, causes, consequences, initial risk assessment, mitigation, residual risk assessment, approval, escalation, monitoring, closure, reporting, and audit trail.

## Created Structure

```text
backend/
frontend/
docs/
docs/codex_tasks/
```

## Created or Updated Files

- `README.md`
- `docs/product_vision.md`
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/data_model.md`
- `docs/codex_tasks/task_001_project_documentation.md`

## Authority Structure

### Low Level: Operational Boards

Default boards:

- Flight Test Safety Committee - Operation
- Aircraft Safety Committee - Engineering Board
- Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE

Low-level boards are configurable. Admin users may create, archive, rename, activate, or deactivate low-level boards.

### Middle Level: Risk Management Committee

Fixed. Cannot be deleted.

### High Level: Executive Safety Management Committee

Fixed. Cannot be deleted.

## Core Requirements Captured

- role-based access control
- complete audit log for all meaningful changes
- DOCX report generation
- LLM-assisted risk structuring from the Problem Description
- PostgreSQL database
- FastAPI backend
- React TypeScript frontend
- modular monolith architecture
- no physical deletion of important records; use archive, deactivate, or closure fields

## Acceptance Criteria

- The folder structure exists.
- The documentation explains the purpose, architecture, authority levels, workflow, data model overview, audit requirement, report requirement, and LLM assistant concept.
- The documentation is clear enough to guide future Codex implementation tasks.

## Status

Completed as documentation-only baseline. No application code was created.
