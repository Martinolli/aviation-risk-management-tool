# Pilot Deployment Checklist

## Purpose

This Pilot Deployment Checklist supports controlled pilot deployment of the Aviation Risk Management Tool before broader operational release. It defines practical go/no-go conditions for limited operational use and provides a structured record for Deployment Readiness, User Acceptance Test completion, Rollback Plan review, Post-Deployment Monitoring, and SMS governance approval.

## Scope

This checklist covers:

- Environment readiness
- Configuration readiness
- Database readiness
- User and access readiness
- SMS governance readiness
- UAT readiness
- Backup/restore readiness
- Security and logging readiness
- Go / No-Go review
- Rollback plan
- Post-deployment monitoring

## Pilot Deployment Assumptions

- Pilot is limited-scope.
- Pilot users are identified.
- Pilot data classification is understood.
- Production use is not authorized until company approval.
- Company SMS, Quality, IT/cybersecurity, and governance functions must approve operational use.

## Required Roles for Pilot Approval

| Role | Responsibility | Required for Go / No-Go | Name | Approval / Comment |
| --- | --- | --- | --- | --- |
| System Owner | Owns application readiness and release coordination. | Yes |  |  |
| SMS / Risk Management Owner | Confirms SMS governance workflow readiness and pilot operating limitations. | Yes |  |  |
| IT / Infrastructure Owner | Confirms environment, database, storage, backup, and operational support readiness. | Yes |  |  |
| Cybersecurity / Data Protection Reviewer | Reviews security configuration, data classification, access controls, and logging exposure. | Yes |  |  |
| Quality / Audit Representative | Reviews controlled records, Audit integrity, defect handling, and approval evidence. | Yes |  |  |
| LOW Authority Level Representative | Confirms LOW Authority Level pilot decision process and membership readiness. | Yes |  |  |
| MIDDLE Authority Level Representative | Confirms MIDDLE Authority Level Risk Management Committee readiness. | Yes |  |  |
| HIGH Authority Level Representative | Confirms HIGH Authority Level Executive Safety Management Committee readiness. | Yes |  |  |
| Pilot User Representative | Confirms pilot user access, training readiness, and practical workflow usability. | Yes |  |  |

## Pre-Deployment Checklist

| ID | Area | Check | Required Evidence | Status | Owner | Comments |
| --- | --- | --- | --- | --- | --- | --- |
| ENV-001 | Environment | Environment selected for pilot | Named pilot environment and access URL | Not Started |  |  |
| ENV-002 | Environment | Backend environment variables configured | Environment variable review record excluding secrets | Not Started |  |  |
| ENV-003 | Environment | Frontend API base URL configured | Frontend build/configuration reference | Not Started |  |  |
| ENV-004 | Environment | Production safety validation passes | Startup log or readiness validation output | Not Started |  |  |
| ENV-005 | Environment | CORS Allowed Origins restricted | Approved frontend origin list | Not Started |  |  |
| ENV-006 | Environment | JWT Secret configured securely | Security owner confirmation without recording secret value | Not Started |  |  |
| ENV-007 | Environment | Development Authentication Fallback disabled | Configuration review showing fallback disabled | Not Started |  |  |
| ENV-008 | Environment | PostgreSQL database available | Database connectivity confirmation | Not Started |  |  |
| ENV-009 | Environment | Alembic migration applied | Migration command output or migration version record | Not Started |  |  |
| ENV-010 | Environment | Evidence Storage path configured | Storage path review and access confirmation | Not Started |  |  |
| ENV-011 | Environment | Generated Reports path configured | Reports path review and access confirmation | Not Started |  |  |
| CI-001 | CI | Backend CI green | Latest backend CI run link or status record | Not Started |  |  |
| CI-002 | CI | Frontend CI green | Latest frontend CI run link or status record | Not Started |  |  |
| CI-003 | CI | Backend health smoke green | Latest backend health smoke result | Not Started |  |  |
| CI-004 | CI | Frontend preview smoke green | Latest frontend smoke result | Not Started |  |  |
| CI-005 | CI | No critical CI warnings unresolved | CI warning review notes | Not Started |  |  |
| DATA-001 | Data | Backup taken before pilot | Backup ID or storage location reference | Not Started |  |  |
| DATA-002 | Data | Restore procedure reviewed | Restore procedure review sign-off | Not Started |  |  |
| DATA-003 | Data | Backup verification completed | Backup verification output or review record | Not Started |  |  |
| DATA-004 | Data | Data retention policy reviewed | Data retention review sign-off | Not Started |  |  |
| DATA-005 | Data | No real sensitive investigation data loaded without approval | Data classification approval or confirmation | Not Started |  |  |
| DATA-006 | Data | Evidence upload storage included in backup scope | Backup scope record | Not Started |  |  |
| DATA-007 | Data | Generated reports storage included in backup scope | Backup scope record | Not Started |  |  |
| ACCESS-001 | Access | Pilot users identified | Pilot user list approved for limited use | Not Started |  |  |
| ACCESS-002 | Access | Admin user configured | Admin account verification record | Not Started |  |  |
| ACCESS-003 | Access | Default/test passwords changed | Password change confirmation without password values | Not Started |  |  |
| ACCESS-004 | Access | Test users disabled or clearly marked | Test user review record | Not Started |  |  |
| ACCESS-005 | Access | LOW Authority Level memberships confirmed | LOW Authority Level membership review | Not Started |  |  |
| ACCESS-006 | Access | MIDDLE Authority Level memberships confirmed | MIDDLE Authority Level membership review | Not Started |  |  |
| ACCESS-007 | Access | HIGH Authority Level memberships confirmed | HIGH Authority Level membership review | Not Started |  |  |
| ACCESS-008 | Access | Permission Matrix reviewed | Permission Matrix review sign-off | Not Started |  |  |
| ACCESS-009 | Access | Unauthorized user access check completed | Unauthorized access test result | Not Started |  |  |
| SMS-001 | SMS governance | Risk matrix seeded and reviewed | Risk matrix review record | Not Started |  |  |
| SMS-002 | SMS governance | Governance committees configured | Committee configuration review | Not Started |  |  |
| SMS-003 | SMS governance | Board of Origin rules reviewed | Board of Origin review notes | Not Started |  |  |
| SMS-004 | SMS governance | Risk workflow reviewed | Workflow review sign-off | Not Started |  |  |
| SMS-005 | SMS governance | Committee decision process reviewed | Committee process review notes | Not Started |  |  |
| SMS-006 | SMS governance | Electronic Approval concept reviewed | Electronic Approval review sign-off | Not Started |  |  |
| SMS-007 | SMS governance | Audit integrity expectations reviewed | Audit integrity review notes | Not Started |  |  |
| SMS-008 | SMS governance | No Hard Delete principle reviewed | Data retention and archive review notes | Not Started |  |  |
| UAT-001 | UAT | UAT Pack completed | Completed User Acceptance Test matrix | Not Started |  |  |
| UAT-002 | UAT | Critical defects closed | Defect log showing no open critical defects | Not Started |  |  |
| UAT-003 | UAT | Major defects reviewed | Major defect disposition record | Not Started |  |  |
| UAT-004 | UAT | UAT sign-off recorded | User Acceptance Test sign-off record | Not Started |  |  |
| UAT-005 | UAT | Open limitations documented | Accepted limitation list | Not Started |  |  |
| LOG-001 | Logging | Production logging configured | Logging configuration review | Not Started |  |  |
| LOG-002 | Logging | Request ID correlation enabled | Response/log sample with Request ID | Not Started |  |  |
| LOG-003 | Logging | Health endpoint verified | `/health` result | Not Started |  |  |
| LOG-004 | Logging | Readiness endpoint verified | `/health/readiness` result | Not Started |  |  |
| LOG-005 | Logging | Logs reviewed for sensitive data exposure | Safe logging review record | Not Started |  |  |
| LOG-006 | Logging | Troubleshooting procedure reviewed | Support procedure review notes | Not Started |  |  |
| DOC-001 | Documentation | Operation limitations documented | Pilot limitation record | Not Started |  |  |
| DOC-002 | Documentation | Backup procedure available | Backup procedure link or copy reference | Not Started |  |  |
| DOC-003 | Documentation | Restore procedure available | Restore procedure link or copy reference | Not Started |  |  |
| DOC-004 | Documentation | Data retention policy available | Data retention policy link or copy reference | Not Started |  |  |
| DOC-005 | Documentation | Permission matrix available | Permission Matrix link or copy reference | Not Started |  |  |
| DOC-006 | Documentation | UAT pack available | UAT Pack link or copy reference | Not Started |  |  |
| DOC-007 | Documentation | Pilot deployment checklist approved | Approved Pilot Deployment Checklist | Not Started |  |  |

Status values:

- Not Started
- Complete
- Not Applicable
- Blocked
- Failed

## Go / No-Go Criteria

| Criterion | Go condition | No-Go condition | Status | Comments |
| --- | --- | --- | --- | --- |
| CI status | Backend CI, frontend CI, backend health smoke, and frontend preview smoke are green. | Any required CI or smoke check is failed or unresolved. | Not Started |  |
| UAT status | User Acceptance Test completed with sign-off and accepted limitations. | UAT incomplete or sign-off missing. | Not Started |  |
| Security configuration | JWT Secret, CORS Allowed Origins, authentication fallback, and data handling are reviewed. | Secret handling or security configuration is unsafe or unreviewed. | Not Started |  |
| Backup/restore readiness | Backup, restore procedure, and verification evidence are complete. | Backup missing, restore path unclear, or verification not completed. | Not Started |  |
| User access readiness | Pilot users, admin access, Authority Level memberships, and unauthorized checks are confirmed. | User access is incomplete, excessive, or not reviewed. | Not Started |  |
| SMS governance readiness | Risk matrix, committees, Board of Origin, approvals, and Audit integrity expectations are reviewed. | SMS governance process is unclear or unapproved. | Not Started |  |
| Logging/readiness diagnostics | Production logging, Request ID, `/health`, and `/health/readiness` are verified. | Diagnostics missing, unsafe, or unreviewed. | Not Started |  |
| Open defects | Critical defects closed and major defects dispositioned. | Open critical defects or unaccepted major defects remain. | Not Started |  |
| Pilot support availability | Support owner and escalation path are assigned for pilot period. | No support owner or escalation path is available. | Not Started |  |

Decision values for `docs/templates/pilot-go-no-go-decision.csv`:

- Go
- Go with limitations
- No-Go
- Blocked

## Pilot Deployment Steps

1. Confirm source branch and commit SHA.
2. Confirm CI green.
3. Confirm environment variables.
4. Confirm database availability.
5. Run migrations.
6. Bootstrap or verify admin user.
7. Seed or verify risk matrix.
8. Verify governance committees.
9. Verify user memberships.
10. Start backend.
11. Start or serve frontend.
12. Check `/health`.
13. Check `/health/readiness`.
14. Login as admin.
15. Login as pilot user.
16. Execute smoke workflow.
17. Record pilot start approval.

## Smoke Workflow After Deployment

- Login.
- View dashboard.
- Create test risk.
- Add initial assessment.
- Submit test risk.
- Verify decision queue.
- Upload test evidence.
- Generate test report.
- Export risk register.
- View audit trail.
- Create electronic approval.
- Confirm request ID appears in response/logs.

## Rollback Plan

- Stop pilot use.
- Notify pilot users.
- Preserve logs.
- Preserve audit records.
- Take emergency backup if needed.
- Restore previous database backup if required.
- Restore previous application version if required.
- Verify `/health` and `/health/readiness`.
- Record rollback decision and reason.

## Post-Deployment Monitoring

First day:

- Check login/access issues.
- Check backend logs.
- Check request IDs for reported errors.
- Check evidence upload.
- Check report generation.
- Check audit trail creation.
- Check export functions.
- Record user feedback.

First week:

- Review defects.
- Review open risks created during pilot.
- Review permission issues.
- Review performance concerns.
- Review backup/restore evidence.
- Review UAT deviations.

## Pilot Limitations

- Not final production release.
- Not certified legal e-signature.
- No external monitoring provider yet.
- No SSO yet.
- No automated retention scheduler yet.
- No cloud backup automation yet.
- No final operation manual yet.

## Pilot Sign-Off

| Field | Value |
| --- | --- |
| Pilot Deployment ID | [To be completed before pilot] |
| Environment | [To be completed before pilot] |
| Version / Commit SHA | [To be completed before pilot] |
| Deployment Date | [To be completed before pilot] |
| Pilot Start Date | [To be completed before pilot] |
| Pilot End Date | [To be completed after pilot] |

Decision:

- Go
- Go with limitations
- No-Go
- Rollback required

| Name | Role | Authority Level | Decision | Date | Comments | Electronic Approval Reference if applicable |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## SMS Governance Note

The Pilot Deployment Checklist supports controlled introduction of the Aviation Risk Management Tool into limited operational use. It does not replace company SMS, Quality, IT/cybersecurity, legal, data protection, or airworthiness governance approval.
