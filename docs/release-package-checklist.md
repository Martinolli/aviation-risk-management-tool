# Version 1.0 Release Package Checklist

## 1. Purpose

This checklist supports review of the Version 1.0 Package before creating the proposed `v1.0.0-pilot` tag. It confirms release documents, Validation Evidence, governance review, release tagging readiness, and post-release actions.

## 2. Required Release Documents

Release documents should be reviewed for consistency, current links, and pilot-readiness wording before final Go / No-Go.

## 3. Required Validation Evidence

Validation evidence should confirm backend tests, frontend build, migration status, CI status, health smoke, and frontend smoke results for the release commit.

## 4. Required Governance Review

Governance review should include SMS, Quality, IT/cybersecurity, pilot users, access/membership readiness, Known Limitations, and accepted release risks.

## 5. Release Tagging Checklist

The release commit must be identified and the Release Notes updated with the commit SHA before creating or pushing a tag. Do not create the tag until final review is complete.

## 6. Post-Release Actions

After release approval, record the tag, monitor pilot readiness, confirm GitHub Actions remain green, and ensure UAT and Pilot Deployment Checklist records are retained.

| ID | Area | Required Item | Status | Evidence / Link | Owner | Comments |
| --- | --- | --- | --- | --- | --- | --- |
| REL-DOC-001 | Release Documents | Release Notes v1.0 | Not Started | [Release Notes v1.0](release-notes-v1.0.md) |  |  |
| REL-DOC-002 | Release Documents | Operation Manual | Not Started | [Operation Manual](operation-manual.md) |  |  |
| REL-DOC-003 | Release Documents | Deployment Readiness Guide | Not Started | [Deployment Readiness Guide](deployment-readiness.md) |  |  |
| REL-DOC-004 | Release Documents | Backup and Restore Procedure | Not Started | [Backup and Restore Procedure](backup-and-restore.md) |  |  |
| REL-DOC-005 | Release Documents | Data Retention and Archive Policy | Not Started | [Data Retention and Archive Policy](data-retention-and-archive-policy.md) |  |  |
| REL-DOC-006 | Release Documents | Permission Matrix | Not Started | [Permission Matrix](permission-matrix.md) |  |  |
| REL-DOC-007 | Release Documents | Electronic Approval Concept | Not Started | [Electronic Approval Concept](electronic-approval-concept.md) |  |  |
| REL-DOC-008 | Release Documents | Production Logging and Monitoring Guide | Not Started | [Production Logging and Monitoring Guide](production-logging-and-monitoring.md) |  |  |
| REL-DOC-009 | Release Documents | UAT Pack | Not Started | [User Acceptance Test Pack](user-acceptance-test-pack.md) |  |  |
| REL-DOC-010 | Release Documents | Pilot Deployment Checklist | Not Started | [Pilot Deployment Checklist](pilot-deployment-checklist.md) |  |  |
| REL-VAL-001 | Validation Evidence | Backend pytest passed | Not Started | TBD |  |  |
| REL-VAL-002 | Validation Evidence | Frontend build passed | Not Started | TBD |  |  |
| REL-VAL-003 | Validation Evidence | Alembic migration passed | Not Started | TBD |  |  |
| REL-VAL-004 | Validation Evidence | Backend CI green | Not Started | TBD |  |  |
| REL-VAL-005 | Validation Evidence | Frontend CI green | Not Started | TBD |  |  |
| REL-VAL-006 | Validation Evidence | Health smoke passed | Not Started | TBD |  |  |
| REL-VAL-007 | Validation Evidence | Frontend smoke passed | Not Started | TBD |  |  |
| REL-GOV-001 | Governance Review | SMS review completed | Not Started | TBD |  |  |
| REL-GOV-002 | Governance Review | Quality review completed | Not Started | TBD |  |  |
| REL-GOV-003 | Governance Review | IT/cybersecurity review completed | Not Started | TBD |  |  |
| REL-GOV-004 | Governance Review | Pilot users identified | Not Started | TBD |  |  |
| REL-GOV-005 | Governance Review | Go / No-Go completed | Not Started | TBD |  |  |
| REL-TAG-001 | Release Tagging | Release commit identified | Not Started | TBD |  |  |
| REL-TAG-002 | Release Tagging | Release notes updated with commit SHA | Not Started | TBD |  |  |
| REL-TAG-003 | Release Tagging | Git tag created | Not Started | TBD |  |  |
| REL-TAG-004 | Release Tagging | Git tag pushed | Not Started | TBD |  |  |

Status values:

- Not Started
- Complete
- Not Applicable
- Blocked
- Failed
