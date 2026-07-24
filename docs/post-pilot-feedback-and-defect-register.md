# Post-Pilot Feedback and Defect Register

## 1. Purpose

This guide defines how pilot findings are captured, classified, reviewed, tracked, and converted into corrective actions or future development tasks after Pilot Execution starts. It supports controlled Post-Pilot Feedback review, Defect Register maintenance, Observation Log review, and release follow-up for the Aviation Risk Management Tool.

## 2. Scope

This guide covers:

- Pilot feedback.
- Defects.
- Observations.
- Enhancement requests.
- Training needs.
- Governance questions.
- Documentation updates.
- Post-pilot decision-making.
- Release follow-up.

It does not add issue tracker integration, GitHub Issues automation, Jira integration, software workflow changes, or real pilot feedback records.

## 3. Relationship to Pilot Execution

Pilot Execution collects raw feedback through the pilot support materials:

- [Pilot Execution Support Pack](pilot-execution-support-pack.md)
- [Pilot Feedback Form](templates/pilot-feedback-form.csv)
- [Pilot Defect Register](templates/pilot-defect-register.csv)
- [Pilot Daily Log](templates/pilot-daily-log.csv)

Pilot execution collects raw feedback. This post-pilot guide controls how that feedback is reviewed, prioritized, and dispositioned. The post-pilot review should preserve Request ID references, evidence references, Severity classification, Disposition decisions, SMS governance concerns, and Audit integrity observations.

## 4. Feedback Categories

| Category | Definition |
| --- | --- |
| Defect | A confirmed failure against expected behavior. |
| Usability Issue | A workflow or interface issue that makes operation confusing, inefficient, or error-prone. |
| Enhancement Request | A requested improvement beyond the approved pilot baseline. |
| Training Need | A finding indicating users need better instruction, examples, or operational guidance. |
| Governance Question | A finding requiring SMS, Quality, IT/cybersecurity, legal, data protection, airworthiness, or management decision. |
| Observation | A useful comment or improvement note that is not yet a defect or approved enhancement. |

## 5. Severity Classification

| Severity | Definition |
| --- | --- |
| Critical | Blocks pilot continuation or creates risk to data integrity, access control, audit integrity, safety governance, or security. |
| Major | Significantly affects a core workflow but workaround may exist. |
| Minor | Limited impact; does not block pilot operation. |
| Observation | No immediate operational impact. |

## 6. Disposition Values

| Disposition | Meaning |
| --- | --- |
| New | Finding has been received but not reviewed. |
| Under Review | Finding is being assessed for validity, impact, owner, and release effect. |
| Accepted | Finding is valid and will be acted on or tracked. |
| Rejected | Finding is not accepted as valid or actionable for the pilot baseline. |
| Duplicate | Finding duplicates another feedback or defect record. |
| Deferred | Finding is valid but deferred outside the current pilot or patch scope. |
| Converted to Task | Finding is converted into a future software, documentation, or operational task. |
| Converted to Training Action | Finding is converted into a training or briefing update. |
| Converted to Governance Action | Finding is converted into an SMS governance, Quality, IT/cybersecurity, legal, data protection, airworthiness, or management action. |
| Fixed | Corrective action has been completed. |
| Verified | Fix or action has been reviewed and accepted by the assigned reviewer. |
| Closed | Finding lifecycle is complete and no further action remains. |

## 7. Review Cadence

During pilot:

- Critical findings reviewed immediately.
- Major findings reviewed daily.
- Minor findings reviewed during pilot review meetings.
- Observations reviewed during closeout.

After pilot:

- Full defect and feedback review.
- Categorize findings.
- Assign owners.
- Decide release impact.
- Create next task list.

## 8. Post-Pilot Review Meeting

Suggested agenda:

1. Review pilot objectives.
2. Review completed pilot scenarios.
3. Review defects by severity.
4. Review access/permission issues.
5. Review workflow gaps.
6. Review reporting/export issues.
7. Review evidence/audit issues.
8. Review electronic approval feedback.
9. Review documentation/training needs.
10. Decide disposition for each finding.
11. Decide whether pilot can continue, expand, pause, or move toward production planning.

## 9. Defect Review Table

| Defect ID | Source | Severity | Feature Area | Description | Request ID | Owner | Disposition | Target Task | Verification Result | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Defect ID] | [Pilot Feedback / UAT / Daily Log] | [Critical / Major / Minor / Observation] | [Feature Area] | [Description] | [Request ID] | [Owner] | [Disposition] | [Target Task] | [Verification Result] | [Status] |

## 10. Feedback Disposition Table

| Feedback ID | Category | Description | Impact | Decision | Owner | Target Task / Action | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Feedback ID] | [Category] | [Description] | [Impact] | [Decision] | [Owner] | [Target Task / Action] | [Status] | [Notes] |

## 11. Conversion to Future Tasks

Accepted findings become future tasks when they require software changes, documentation changes, training actions, governance review, release planning, or verification work. Each converted task should retain the source Feedback ID or Defect ID, category, Severity, Request ID if available, owner, acceptance criteria, and target release.

Task examples:

- Task 100 - Pilot Feedback Consolidation Report.
- Task 101 - Critical Defect Corrections.
- Task 102 - UAT / Pilot Usability Improvements.
- Task 103 - Training Material Updates.
- Task 104 - Governance Rule Adjustments.
- Task 105 - LLM Advisory Interface Concept and Guardrails.

## 12. Release Impact Decision

| Release Impact | Definition |
| --- | --- |
| No release impact | Finding does not affect pilot baseline. |
| Patch release required | Fix needed before continuing or expanding pilot. |
| Documentation/training update required | No software change, but manual or training update needed. |
| Governance decision required | Requires SMS/Quality/IT/cybersecurity/legal/airworthiness review. |
| Future enhancement | Candidate for future version. |

## 13. Patch Release Recommendation

If critical or major defects require software correction, create a patch release plan:

- Identify baseline version.
- Identify fix commits.
- Run full tests.
- Update release notes.
- Create patch tag.
- Communicate changes to pilot users.

Possible tag examples:

- v1.0.1-pilot.
- v1.0.2-pilot.

Patch tags must be created only after approval and should preserve the relationship to the tested pilot baseline.

## 14. Post-Pilot Closeout Report Outline

- Executive summary.
- Pilot scope.
- Version tested.
- Participants.
- Scenarios completed.
- Defects found.
- Feedback summary.
- Open issues.
- Governance concerns.
- Recommended next steps.
- Decision recommendation.

Use [post-pilot-closeout-report-template.md](templates/post-pilot-closeout-report-template.md) to prepare the controlled closeout report.

## 15. SMS Governance Note

The Post-Pilot Feedback and Defect Register supports controlled pilot learning and continuous improvement. It does not replace company SMS governance, Quality, IT/cybersecurity, legal, data protection, or airworthiness governance decision-making.
