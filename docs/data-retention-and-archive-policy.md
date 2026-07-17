# Data Retention and Archive Policy

## Purpose

This Data Retention and Archive Policy protects SMS governance records, risk decisions, the audit trail, evidence, generated reports, exports, and committee records for the Aviation Risk Management Tool. It defines MVP expectations for Retention Period, Archive Review, No Hard Delete guardrails, Audit integrity, and Evidence traceability.

## Scope

This policy covers:

- Risk records
- Assessments
- Decisions
- Mitigation actions
- Monitoring reviews
- Evidence uploads
- Generated reports
- Audit logs
- Committee meetings and minutes
- User/role records
- Backups
- Exports

## Core Principles

- No hard delete for governed SMS records.
- Archive instead of delete.
- Audit integrity must be preserved.
- Evidence traceability must be maintained.
- Legal, investigation, airworthiness, and regulatory holds override normal retention.
- Retention periods must be approved by company policy.
- SMS governance records must remain available for audit preparation, management review, and investigation support.
- Evidence Preservation requires evidence and metadata to remain linked to the applicable risk record.

## Retention Matrix

| Record Type | Minimum Retention | Archive Rule | Deletion Rule | Responsible Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Risk Records | Minimum 10 years or company SMS/airworthiness requirement, whichever is longer. | Closed risks may be archived after management review. | No hard delete in MVP. | SMS / risk management owner | Archive Review should confirm closure, actions, monitoring, and holds. |
| Risk Assessments | Same as parent risk record. | Inherited from risk record. | No hard delete. | SMS / risk management owner | Supports historical risk evaluation and decision traceability. |
| Risk Decisions | Same as parent risk record. | Inherited from risk record. | No hard delete. | Decision authority / committee owner | Decision records are governed SMS records. |
| Mitigation Actions | Same as parent risk record. | Inherited from risk record. | No hard delete. | Action owner / SMS owner | Actions must remain traceable to the risk they mitigate. |
| Monitoring Reviews | Same as parent risk record. | Closed/cancelled reviews remain linked to parent risk. | No hard delete. | Monitoring owner / SMS owner | Retain evidence of ongoing risk control effectiveness. |
| Evidence Uploads | Same as parent risk record or investigation/legal hold requirement. | Evidence may be archived from active view but remains stored. | No hard delete in MVP. | Evidence owner / SMS owner | Evidence Preservation requires traceability to the risk record. |
| Generated Reports | Minimum 10 years or according to SMS audit/committee record policy. | May be moved to controlled archive storage. | No hard delete without approved records disposition process. | SMS / quality records owner | Reports used for official review become controlled records. |
| Audit Logs | Permanent or as required by company SMS governance. | May be moved to long-term immutable archive. | No manual deletion. | SMS governance / cybersecurity owner | Audit Integrity must be preserved for operational traceability. |
| Committee Meetings and Minutes | Minimum 10 years or company governance requirement. | Finalized meetings remain retained. | No hard delete. | Committee secretary / governance owner | Committee records support governance and audit preparation. |
| User and Role Records | Retain while associated records exist. | Deactivate users instead of deletion. | No hard delete when linked to governance records. | System administrator / cybersecurity owner | Identity references must remain understandable for audit review. |
| Backups | Defined by company IT/security. | Rotate according to approved backup retention schedule. | Deletion only according to approved backup retention policy. | Company IT/security | Backups do not replace formal SMS records retention. |
| Exports | Treat exported files as controlled records if used for committee, audit, or management review. | Store in approved location. | Follow company records policy. | Exporting user / records owner | Exports may contain sensitive SMS governance and evidence data. |

## Archive Process

1. Confirm the risk or record is closed or inactive.
2. Confirm no open actions or monitoring reviews remain.
3. Confirm no investigation, legal, airworthiness, or regulatory hold applies.
4. Record the archive reason.
5. Archive the record through the application workflow.
6. Verify the audit log entry.
7. Keep evidence and reports traceable.

## Restore Process

1. Confirm the business reason.
2. Confirm authority approval.
3. Restore the archived record if supported.
4. Record the restore reason.
5. Verify the audit log entry.

## Legal / Investigation Hold

If a record is related to an occurrence, incident, accident, regulatory inquiry, legal matter, certification issue, airworthiness limitation, or active investigation, normal archive/deletion schedules are suspended.

## Backup Relationship

Backups are operational recovery copies and do not replace formal records retention. Backup retention must be approved by company IT/security and aligned with cybersecurity expectations. See the [Backup and Restore Procedure](backup-and-restore.md).

## Generated Exports

Exported risk registers, audit trails, evidence packages, and committee packs become controlled records when used for official review or decision-making. They should be stored in an approved location and handled according to company records policy.

## Known MVP Limitations

- No automatic retention scheduler.
- No automatic purge.
- No immutable storage.
- No legal-hold workflow flag yet.
- No records-disposition approval workflow yet.

## Future Improvements

- Legal hold flag
- Retention review queue
- Archive review dashboard
- Records disposition approval workflow
- Immutable audit storage
- Automated backup retention
- Configurable retention periods by record type

## SMS Governance Note

"The application supports SMS governance and audit preparation. Final retention periods, legal holds, and records disposition rules must be approved by company quality, SMS, legal, cybersecurity, and applicable airworthiness governance functions."
