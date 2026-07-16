# Backup and Restore Procedure

## Purpose

This Backup and Restore procedure protects SMS governance data, risk records, audit trail, evidence uploads, generated reports, committee records, and supporting operational records for the Aviation Risk Management Tool.

## Scope

This MVP covers local development, pilot deployment, and early production preparation. It does not replace enterprise IT backup policy, approved disaster recovery planning, or cybersecurity requirements.

## Backup Assets

| Asset | Backup Responsibility | Notes |
| --- | --- | --- |
| PostgreSQL database | Database Backup | Contains structured SMS records, risk records, audit trail, committee decisions, users, roles, and workflow state. |
| Evidence uploads | Evidence Backup | Files on disk under the configured evidence storage path. These may contain sensitive investigation and operational data. |
| Generated reports | Generated Reports Backup | Files on disk under the configured generated reports path, including DOCX reports and controlled exports. |
| Environment variables/secrets | Managed separately | Secrets are not backed up by the script. Store them in an approved secret manager or secure operating procedure. |
| Source code repository | Git/GitHub | Source code is backed up through Git and GitHub, not by the operational backup script. |

## Recovery Objectives

- Recovery Point Objective: draft MVP target is maximum 24 hours of acceptable data loss for pilot/internal use unless the company defines a stricter value.
- Recovery Time Objective: draft MVP target is same business day restoration for pilot/internal use.

These RPO and RTO values require company approval before production use.

## Local Backup Procedure

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local.ps1
```

The script creates a timestamped folder under `backups/`, runs a PostgreSQL custom-format Database Backup from the Docker container, copies Evidence Backup files when present, copies Generated Reports Backup files when present, and writes `backup_manifest.json`.

## Verify Backup

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-backup-local.ps1 -BackupPath backups/backup_YYYYMMDD_HHMMSS
```

This validates that `database.dump` and `backup_manifest.json` exist, parses the manifest, checks evidence and generated reports folder presence against the manifest, and prints file counts.

## Local Restore Procedure

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore-local.ps1 -BackupPath backups/backup_YYYYMMDD_HHMMSS
```

The Restore Procedure warns before replacing local database data and overwriting evidence/generated report folders. Pass `-Force` only for automated local restore drills where the backup path has already been verified.

## Production Backup Guidance

- Use managed PostgreSQL backups or scheduled `pg_dump`.
- Store backups outside the application server.
- Protect backups with encryption at rest.
- Restrict access to approved administrators.
- Test restore periodically.
- Retain backup logs.
- Define retention period.
- Include evidence uploads and generated reports storage in backup scope.
- Validate that database and file backups are taken at compatible times.

## Restore Test Procedure

1. Restore into a non-production environment.
2. Run `alembic current`.
3. Start the backend.
4. Check `/health` and `/health/readiness`.
5. Login as admin.
6. Confirm the risk list loads.
7. Confirm evidence links/downloads work.
8. Confirm generated reports path works.
9. Run selected smoke tests.

## Backup Security

- Backups may contain sensitive SMS, investigation, operational, and personnel data.
- Do not commit backups.
- Do not email unprotected backups.
- Store backups in an approved secure location.
- Limit access.
- Follow company cybersecurity and data protection rules.

## Audit Integrity Note

Restore operations must be documented. Production restore should be approved and logged. Restored audit trail should not be manually edited. Preserving Audit integrity is required for SMS governance and operational traceability.

## Known Limitations

- Scripts are local MVP helpers.
- No encryption automation yet.
- No cloud backup automation yet.
- No scheduled backup yet.
- No production restore automation yet.

## Future Improvements

- Scheduled backups.
- Encrypted backup archives.
- Backup retention automation.
- Restore drill checklist.
- Admin UI backup status.
- Storage provider integration.
- Automated backup verification.
