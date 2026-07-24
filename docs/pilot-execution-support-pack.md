# Pilot Execution Support Pack

## 1. Purpose

This Pilot Execution Support Pack supports controlled Pilot Execution of the Aviation Risk Management Tool after the v1.0.0-pilot baseline. It provides reusable operational material for preparing pilot users, executing planned pilot sessions, capturing Pilot Feedback, tracking defects, reviewing observations, and closing out the pilot before broader release decisions.

## 2. Scope

This pack covers:

- Pilot preparation.
- Pilot User Briefing.
- Test data guidance.
- Execution schedule.
- Daily pilot monitoring.
- Feedback capture.
- Defect handling.
- Support contacts/placeholders.
- Pilot closeout.

This pack does not add deployment automation, create real pilot data, replace company approval processes, or introduce new application business logic.

## 3. Pilot Baseline

| Field | Value |
| --- | --- |
| Application | Aviation Risk Management Tool |
| Version | v1.0.0-pilot |
| Release status | Pilot Release Candidate |
| Release tag | v1.0.0-pilot |
| Release notes | [docs/release-notes-v1.0.md](release-notes-v1.0.md) |
| Operation manual | [docs/operation-manual.md](operation-manual.md) |

## 4. Pilot Objectives

- Validate normal SMS risk workflow.
- Validate Authority Level governance.
- Validate committee decision workflow.
- Validate evidence traceability.
- Validate reports and exports.
- Validate audit trail.
- Validate electronic approval concept.
- Validate dashboards and notifications.
- Identify usability issues.
- Identify configuration/access issues.
- Confirm readiness gaps before broader release.

## 5. Pilot Participants

| Role | Responsibility | Example User | Required Access | Authority Level |
| --- | --- | --- | --- | --- |
| Pilot Coordinator | Coordinates Pilot Execution schedule, evidence collection, daily reviews, and closeout. | [Name] | Pilot coordination records and all support templates | As assigned |
| System Administrator | Creates pilot users, configures roles, and manages governed admin setup. | [Name] | Admin governance and user management | As assigned |
| SMS / Risk Owner | Creates and manages pilot risk records and workflow evidence. | [Name] | Risk creation, package, assessment, actions, evidence, reports | As assigned |
| LOW Authority Level Committee Member | Reviews Board of Origin decisions during pilot scenarios. | [Name] | LOW committee queue and assigned risk records | LOW |
| MIDDLE Authority Level Committee Member | Reviews Risk Management Committee scenarios and escalation paths. | [Name] | MIDDLE committee queue and assigned risk records | MIDDLE |
| HIGH Authority Level Committee Member | Reviews executive safety committee scenarios and high authority decisions. | [Name] | HIGH committee queue and assigned risk records | HIGH |
| Action Owner | Completes assigned mitigation actions and records completion evidence. | [Name] | My Actions and assigned action records | As assigned |
| Monitoring Owner | Completes monitoring reviews and records follow-up notes. | [Name] | My Monitoring and assigned monitoring records | As assigned |
| Management Viewer | Reviews dashboard summaries and management indicators. | [Name] | Management dashboard and authorized summary views | As assigned |
| IT / Technical Support | Supports login, environment, logs, Request ID correlation, backup, and restore review. | [Name] | Technical support records and operational logs | As assigned |
| Quality / Audit Reviewer | Reviews Audit integrity, evidence traceability, defects, observations, and closeout records. | [Name] | Audit Trail, controlled exports, and pilot support records | As assigned |

## 6. Pilot Preparation Checklist

| ID | Preparation Item | Required Evidence | Owner | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| PILOT-PREP-001 | Confirm v1.0.0-pilot tag | Tag reference or release record | [Owner] | Not Started |  |
| PILOT-PREP-002 | Confirm CI green | Backend CI, frontend CI, backend health smoke, and frontend smoke result | [Owner] | Not Started |  |
| PILOT-PREP-003 | Confirm deployment readiness checklist complete | Completed Pilot Deployment Checklist | [Owner] | Not Started |  |
| PILOT-PREP-004 | Confirm backup taken | Backup ID or backup evidence reference | [Owner] | Not Started |  |
| PILOT-PREP-005 | Confirm restore procedure reviewed | Restore review sign-off or review notes | [Owner] | Not Started |  |
| PILOT-PREP-006 | Confirm pilot users created | Approved pilot user list without passwords | [Owner] | Not Started |  |
| PILOT-PREP-007 | Confirm Authority Level memberships configured | Membership review record | [Owner] | Not Started |  |
| PILOT-PREP-008 | Confirm test data boundaries | Data classification approval or pilot data boundary statement | [Owner] | Not Started |  |
| PILOT-PREP-009 | Confirm support contact | Named support owner and escalation path | [Owner] | Not Started |  |
| PILOT-PREP-010 | Confirm UAT Pack available | Link or controlled copy reference | [Owner] | Not Started |  |
| PILOT-PREP-011 | Confirm Operation Manual available | Link or controlled copy reference | [Owner] | Not Started |  |
| PILOT-PREP-012 | Confirm pilot feedback forms/templates available | Template links or controlled copy references | [Owner] | Not Started |  |

## 7. Pilot User Briefing

Use this Pilot User Briefing outline before pilot access is granted:

- Purpose of the tool.
- Pilot limitations.
- How to login.
- Where to find the Operation Manual.
- Normal workflow overview.
- What users should test.
- What users should not do.
- How to report defects.
- How to capture Request ID.
- How to handle sensitive data.
- How to request support.

Briefing completion should be recorded by the Pilot Coordinator before each participant begins pilot activities.

Support contacts/placeholders:

| Support Area | Contact / Owner | Availability | Escalation Notes |
| --- | --- | --- | --- |
| Pilot coordination | [Name / team] | [Pilot hours] | [Escalation path] |
| Application administration | [Name / team] | [Pilot hours] | [Escalation path] |
| IT / technical support | [Name / team] | [Pilot hours] | [Escalation path] |
| SMS / governance support | [Name / team] | [Pilot hours] | [Escalation path] |
| Quality / audit support | [Name / team] | [Pilot hours] | [Escalation path] |

## 8. Pilot Test Data Guidance

- Use non-sensitive sample risk records unless approved.
- Avoid real accident/investigation/classified/export-controlled data.
- Mark pilot/test records clearly.
- Use realistic but non-sensitive evidence files.
- Record any use of real data with approval.
- Preserve audit trail during pilot.

Pilot data must remain generic unless company governance approves a controlled exception. Evidence files should support evidence traceability without exposing sensitive information.

## 9. Pilot Execution Schedule Template

| Day / Session | Focus Area | Participants | Planned Activities | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| Session 1 | Login, navigation, dashboards | Pilot users, System Administrator | Verify login, navigation, dashboard access, notifications | Session notes, access observations, Request ID if issue occurs | Not Started |
| Session 2 | Risk creation and package completion | SMS / Risk Owner | Create marked pilot risk records and complete package details | Risk record references, package completion notes | Not Started |
| Session 3 | Initial assessment and submission | SMS / Risk Owner, LOW member | Complete initial assessment and submit to Board of Origin | Assessment record, submission observation, audit trail entry | Not Started |
| Session 4 | Committee decision and escalation | LOW, MIDDLE, HIGH members | Record decisions, escalation, return, or acceptance scenarios | Decision records, queue observations, audit trail entries | Not Started |
| Session 5 | Mitigation actions and residual risk | SMS / Risk Owner, Action Owner | Create and complete mitigation actions; review residual risk | Action records, residual assessment notes | Not Started |
| Session 6 | Monitoring and evidence | Monitoring Owner, SMS / Risk Owner | Complete monitoring review and upload approved evidence | Monitoring record, evidence reference, audit trail entries | Not Started |
| Session 7 | Reports, exports, audit trail | SMS / Risk Owner, Quality / Audit Reviewer | Generate reports, exports, and audit trail review evidence | Report/export references, audit review notes | Not Started |
| Session 8 | Admin governance and permissions | System Administrator, Quality / Audit Reviewer | Review users, roles, committee memberships, and access boundaries | Permission review notes, access issue records | Not Started |
| Session 9 | Electronic approval concept | Authorized approvers, Quality / Audit Reviewer | Create controlled approval records and review limitations | Approval references, Audit integrity observations | Not Started |
| Session 10 | Pilot closeout and feedback review | Pilot Coordinator, all leads | Review feedback, defects, observations, and recommendation | Closeout recommendation and sign-off notes | Not Started |

## 10. Daily Pilot Monitoring

Daily pilot monitoring should include:

- Review new defects.
- Review access issues.
- Review failed workflows.
- Check backend logs/request IDs.
- Check audit trail entries.
- Check evidence uploads.
- Check generated reports.
- Review user feedback.
- Decide whether pilot continues, pauses, or needs corrective action.

Record daily monitoring in [pilot-daily-log.csv](templates/pilot-daily-log.csv). Material observations may also be tracked as an Observation Log entry in the feedback or defect review record.

Daily log decision values:

- Continue.
- Continue with limitations.
- Pause.
- Rollback.
- Close Pilot.

## 11. Pilot Feedback Process

Each user should submit Pilot Feedback for relevant pilot sessions. The Pilot Coordinator should classify submissions as one of:

- Defect.
- Usability issue.
- Enhancement Request.
- Training need.
- Governance question.
- Observation.

Critical and major issues should be reviewed daily. Feedback should be reviewed before pilot closeout and retained with the pilot record.

Use [pilot-feedback-form.csv](templates/pilot-feedback-form.csv) for Pilot Feedback collection.

## 12. Defect and Observation Handling

Use the Defect Register to record, review, assign, disposition, and close defects found during Pilot Execution. Observations should remain traceable even when they do not require a software fix.

Severity definitions:

- Critical: blocks pilot or risks data/security/governance integrity.
- Major: significant workflow or access issue.
- Minor: limited issue or workaround exists.
- Observation: feedback, improvement, or clarification.

Status values:

- New.
- Under Review.
- Accepted.
- In Progress.
- Fixed.
- Deferred.
- Rejected.
- Closed.

Use [pilot-defect-register.csv](templates/pilot-defect-register.csv) as the pilot Defect Register.

## 13. Pilot Closeout

Pilot closeout activities:

- Review completed scenarios.
- Review open defects.
- Review feedback.
- Review access/permission findings.
- Review documentation gaps.
- Review training needs.
- Review whether broader pilot or production preparation is recommended.

Closeout should preserve the final Pilot Feedback summary, Defect Register, daily log, and any Observation Log entries needed for governance review.

## 14. Pilot Closeout Recommendation

Select one closeout recommendation:

- Continue pilot.
- Expand pilot.
- Accept with limitations.
- Re-test required.
- Stop pilot / rollback.
- Prepare production deployment plan.

Record the rationale, unresolved issues, accepted limitations, and required governance approvals before changing pilot scope.

## 15. Post-Pilot Feedback and Defect Register

After Pilot Execution, pilot feedback should be consolidated using the post-pilot register. The Post-Pilot Feedback and Defect Register process controls how Pilot Feedback, defects, Observation Log entries, Enhancement Request items, Training Need findings, and Governance Question items are reviewed, prioritized, dispositioned, and converted into future work.

Post-pilot support materials:

- [Post-Pilot Feedback and Defect Register](post-pilot-feedback-and-defect-register.md)
- [Post-Pilot Feedback Register](templates/post-pilot-feedback-register.csv)
- [Post-Pilot Closeout Report Template](templates/post-pilot-closeout-report-template.md)
- [Post-Pilot Task Backlog](templates/post-pilot-task-backlog.csv)

## 16. SMS Governance Note

The Pilot Execution Support Pack supports controlled pilot operation and feedback collection. It does not replace company SMS governance, Quality, IT/cybersecurity, legal, data protection, or airworthiness governance approval.
