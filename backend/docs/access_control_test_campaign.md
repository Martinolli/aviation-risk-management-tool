# Access-Control Test Campaign

## 1. Purpose

This campaign verifies that the Risk Management Process Tool applies one consistent authorization scope to risk lists, risk details, reports, audit logs, and committee decisions. It combines automated backend coverage with a repeatable manual frontend campaign. The campaign must detect metadata leakage as well as denied write operations.

## 2. Access-Control Principles

- Users only see risks they are authorized to open.
- Risk list and risk detail authorization must match.
- Board of Origin controls LOW-level committee visibility and decision authority.
- Active members of fixed MIDDLE/HIGH governance committees have governance read visibility.
- System Admin does not automatically equal Governance Administrator.
- Governance Administrator access is represented by active Risk Management Committee membership, or another active fixed governance committee membership.
- Creator, owner, assessment performer, action owner, decision maker, and active members of a committee that made a decision retain the related risk access described by the access service.
- Reports and audit logs follow the access scope of their linked risk.
- Inactive users, inactive memberships, and memberships in inactive committees grant no access.
- Unauthorized requests return a clear authorization error or an empty authorized collection, never partial risk/report/audit metadata.
- Bearer-token authentication is the real user path. Test-only identity headers remain limited to existing backend API test utilities.

## 3. Test Accounts

| Account | Responsibility / membership | Authority | Committee role |
|---|---|---:|---|
| `admin@example.com` | Bootstrap Governance Administrator; Risk Management Committee | MIDDLE | Governance Administrator |
| `joao.bosco@calidus.ae` | System Admin responsibility and active Risk Management Committee governance membership | MIDDLE | Governance Administrator |
| `kevin.rooney@calidus.ae` | Aircraft Safety Committee - Engineering Board | LOW | Committee Chairman |
| `gulzar.hussain@calidus.ae` | Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE | LOW | Committee Member |
| `joao.desouza@calidus.ae` | Flight Test Safety Committee - Operation | LOW | Committee Chairman |
| `andres.samper@calidus.ae` | Risk Management Committee | MIDDLE | Committee Member |
| `celso.cobra@calaero.ae` | Risk Management Committee | MIDDLE | Committee Chairman |

`joao.bosco@calidus.ae` deliberately holds two distinct responsibilities. His broad risk visibility comes from active fixed RMC membership, not from the System Admin responsibility.

## 4. Committee / Authority Model

| Authority | Expected committee model | Read scope | Decision scope |
|---|---|---|---|
| LOW | Configurable operational Board of Origin | Risks assigned to that board, plus risks where the user is otherwise involved | Only risks whose Board of Origin is that committee |
| MIDDLE | Fixed Risk Management Committee | All active risks through fixed-governance membership | Risks escalated to the Risk Management Committee |
| HIGH | Fixed Executive Safety Management Committee | All active risks through fixed-governance membership | Risks escalated to the Executive committee; cannot escalate further |

Only active users with active membership in an active committee receive committee-derived authority. A non-fixed MIDDLE/HIGH committee does not grant fixed-governance visibility or authority.

## 5. Risk Visibility Matrix

Legend: **Y** = expected in the list; **N** = must not appear; **Y\*** = remains visible through Board of Origin or prior involvement after escalation.

| Account / role | Flight Test risk | Quality / Industrial risk | Engineering / Aircraft risk | Boardless risk | Risk escalated to RMC |
|---|:---:|:---:|:---:|:---:|:---:|
| Bootstrap Governance Administrator (`admin@example.com`) | Y | Y | Y | Y | Y |
| Joao Bosco, RMC Governance Administrator | Y | Y | Y | Y | Y |
| Andres / Celso, RMC member or chairman | Y | Y | Y | Y | Y |
| Joao De Souza, Flight Test LOW | Y | N | N | N | Y\* when originating from Flight Test |
| Gulzar Hussain, Industrial LOW | N | Y | N | N | Y\* when originating from Industrial |
| Kevin Rooney, Aircraft LOW | N | N | Y | N | Y\* when originating from Aircraft |
| System Admin with no governance membership and no risk involvement | N | N | N | N | N |

Creator, assigned owner, assessment performer, action owner, decision maker, and eligible decision-committee members can see the specific related risk even when a committee-only cell above is `N`.

## 6. Risk Detail Access Matrix

| Condition | List result | `GET /risks/{id}/detail` |
|---|---|---|
| Authorized by Board of Origin, fixed governance, or direct involvement | Risk is present | 200 with full authorized detail |
| Not authorized | Risk is absent; no metadata is returned | Clear authorization error |
| Unauthenticated, unknown, or inactive user | No list data | Authentication/active-user error |
| Inactive membership or inactive committee only | Risk is absent | Authorization error |

For every automated list assertion, the campaign also attempts the corresponding detail URL so list and open behavior cannot diverge.

## 7. Decision Authority Matrix

| Decision context | LOW Board of Origin | MIDDLE RMC | HIGH fixed committee |
|---|:---:|:---:|:---:|
| Approve / reject / return at own stage | Allowed | Allowed after escalation to RMC | Allowed after escalation to Executive committee |
| Escalate | Allowed to RMC | Allowed to Executive committee | Denied; HIGH cannot escalate further |
| Accept residual risk | Allowed only when LOW residual-risk rules pass | Allowed at RMC stage | Allowed at HIGH stage |
| Close | Allowed only with tolerable residual risk and completed/cancelled mitigation actions | Allowed at RMC stage | Allowed at HIGH stage |
| Member of another LOW committee | Denied | Not applicable | Not applicable |
| Direct POST without active membership | Denied | Denied | Denied |

## 8. Report Access Matrix

| Operation | Authorized linked-risk reader | Unauthorized user | Unauthenticated user |
|---|:---:|:---:|:---:|
| Generate risk dossier | Allowed | Denied | Denied |
| List with `risk_record_id` | Only authorized reports | Empty authorized result; no report metadata | Denied |
| List without risk filter | Reports for readable risks only | No out-of-scope reports | Denied |
| Get report metadata | Allowed | Denied | Denied |
| Download report | Allowed | Denied | Denied |

Unlinked reports are not exposed by authorized report list/get operations.

## 9. Audit Trail Access Matrix

| Audit entity | Authorization source |
|---|---|
| `RiskRecord` | Linked risk access |
| `RiskAssessment` | Linked risk access, including assessment involvement |
| `RiskAction` | Linked risk access, including action ownership |
| `RiskDecision` | Linked risk access, decision maker, or active decision-committee membership |
| `GeneratedReport` | Linked risk access |
| User / membership administrative records | The affected user where supported, otherwise fixed governance scope |

Both list filtering and direct `GET /audit-logs/{id}` use the same scope. `entity_type`, `entity_id`, action, actor, limit, and offset parameters must never bypass authorization. System Admin responsibility alone does not grant all risk audit logs.

## 10. Manual Frontend Validation Checklist

- [ ] From `backend`, run `python -m app.cli seed-test-access-profiles --password ChangeMe123!`.
- [ ] Create a Flight Test risk assigned to **Flight Test Safety Committee - Operation**.
- [ ] Create a Quality risk assigned to **Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE**.
- [ ] Create an Engineering risk assigned to **Aircraft Safety Committee - Engineering Board**.
- [ ] Log in as `joao.bosco@calidus.ae`; confirm My Queue shows Risk Management Committee, Authority Level MIDDLE, and Governance Administrator.
- [ ] As Joao Bosco, open all three risk details and confirm reports and audit trail follow governance scope.
- [ ] Log in as `gulzar.hussain@calidus.ae`; confirm only the Quality/Industrial risk appears and direct URLs for Flight Test and Engineering are denied.
- [ ] Log in as `joao.desouza@calidus.ae`; confirm only the Flight Test risk appears and Quality/Engineering direct access is denied.
- [ ] Log in as `kevin.rooney@calidus.ae`; confirm only the Engineering risk appears and Quality/Flight Test direct access is denied.
- [ ] Log in as `admin@example.com`; confirm bootstrap Governance Administrator behavior.
- [ ] Confirm Reports shows no report outside the current account's risk scope.
- [ ] Confirm Audit Trail shows no audit log outside the current account's risk scope.
- [ ] Paste direct report, report-download, risk-detail, and audit-log URLs from another account and confirm denial without leaked metadata.
- [ ] Confirm no page crashes when an authorization error is returned.

## 11. Known Negative Cases

- System Admin responsibility without active fixed governance membership.
- Inactive user, inactive committee membership, or inactive committee.
- LOW member accessing or deciding another Board of Origin's risk.
- LOW member accessing a boardless risk without direct involvement.
- Non-fixed MIDDLE committee treated as governance.
- Report list/get/download for another board's risk.
- Audit filter targeting an unauthorized entity ID.
- Direct audit-log GET for an unauthorized child entity.
- HIGH committee attempting to escalate.
- LOW acceptance or closure with missing/non-tolerable/escalating residual assessment.
- LOW closure while mitigation actions remain open or in progress.
- Any unauthenticated risk list/detail, report list/get/download, audit list/get, or decision POST.

## 12. Acceptance Criteria

- This campaign document exists and its matrices match automated expectations.
- Automated tests cover risk list/detail access for the three LOW boards, fixed governance users, directly involved users, unauthenticated users, and a System Admin without governance membership.
- Risk lists return no unauthorized risk metadata.
- Report generation, list, get, and download follow linked-risk access and expose no unauthorized report metadata.
- Audit list, filters, child-entity scope, and direct get follow linked-risk access.
- Decision tests enforce Board of Origin, escalation stage, decision-type limits, residual tolerability, and mitigation completion.
- Seed tests verify Joao Bosco is active, is profiled for System Admin responsibility, and separately has active RMC membership with role label `Governance Administrator`.
- Seed tests preserve `celso.cobra@calaero.ae` exactly.
- Full backend `pytest` passes.
- Frontend build is required only if frontend files are changed.
