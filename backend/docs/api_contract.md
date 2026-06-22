# Backend API Contract — MVP

## Purpose

This document summarizes the MVP backend API contract for frontend development
and integration testing. It complements the interactive OpenAPI documentation
at `/docs`; OpenAPI remains the source for full request and response schemas.

## Base URL

Local development base URL: `http://127.0.0.1:8000`

## Authentication

Use JWT Bearer authentication for frontend requests to protected endpoints:

```text
Authorization: Bearer <access_token>
```

Log in with `POST /auth/login`:

```json
{
  "email": "admin@example.com",
  "password": "ChangeMe123!"
}
```

The successful response contains `access_token`, `token_type`, `expires_in`,
and `user`. Use `GET /auth/me` to retrieve the authenticated user and restore
a frontend session.

`X-User-Id` is a temporary development/testing compatibility fallback. It is
controlled by `ENABLE_X_USER_ID_AUTH_FALLBACK`, which defaults to `false`; do
not use it in a frontend production flow. A supplied Bearer token always takes
precedence, and an invalid Bearer token is not bypassed by this fallback.

## Standard error response

Normal API errors use this shape:

```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Authentication required",
    "details": {}
  }
}
```

Common codes are `BAD_REQUEST`, `UNAUTHENTICATED`, `FORBIDDEN`, `NOT_FOUND`,
`CONFLICT`, `VALIDATION_ERROR`, `BUSINESS_RULE_VIOLATION`, and
`INTERNAL_SERVER_ERROR`.

Validation failures return HTTP 422 and include field metadata without echoing
submitted values:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "errors": [
        {
          "type": "missing",
          "loc": ["body", "password"],
          "msg": "Field required"
        }
      ]
    }
  }
}
```

## Endpoint inventory

`{...}` path segments are UUID identifiers. Collection list endpoints support
the filters shown in OpenAPI where applicable.

| Area | Method | Path | Purpose |
| --- | --- | --- | --- |
| Health | GET | `/health` | Service health status. |
| Auth | POST | `/auth/login` | Authenticate and receive a JWT. |
| Auth | GET | `/auth/me` | Return the current authenticated user. |
| Users | GET, POST | `/users` | List users or create a user. |
| Users | GET, PATCH | `/users/{user_id}` | Read or update a user. |
| Roles | GET, POST | `/roles` | List roles or create a role. |
| Roles | GET, PATCH | `/roles/{role_id}` | Read or update a role. |
| Committees | GET, POST | `/committees` | List committees or create a committee. |
| Committees | GET, PATCH | `/committees/{committee_id}` | Read or update a committee. |
| Committees | POST | `/committees/{committee_id}/archive` | Archive a committee. |
| Committee Members | GET, POST | `/committee-members` | List or create committee memberships. |
| Committee Members | GET, PATCH | `/committee-members/{committee_member_id}` | Read or update a membership. |
| Risk Matrix | GET, POST | `/risk-matrix/severity-levels` | List or create severity levels. |
| Risk Matrix | GET, PATCH | `/risk-matrix/severity-levels/{severity_level_id}` | Read or update a severity level. |
| Risk Matrix | POST | `/risk-matrix/severity-levels/{severity_level_id}/archive` | Archive a severity level. |
| Risk Matrix | GET, POST | `/risk-matrix/likelihood-levels` | List or create likelihood levels. |
| Risk Matrix | GET, PATCH | `/risk-matrix/likelihood-levels/{likelihood_level_id}` | Read or update a likelihood level. |
| Risk Matrix | POST | `/risk-matrix/likelihood-levels/{likelihood_level_id}/archive` | Archive a likelihood level. |
| Risk Matrix | GET, POST | `/risk-matrix/risk-levels` | List or create risk levels. |
| Risk Matrix | GET, PATCH | `/risk-matrix/risk-levels/{risk_level_id}` | Read or update a risk level. |
| Risk Matrix | POST | `/risk-matrix/risk-levels/{risk_level_id}/archive` | Archive a risk level. |
| Risk Matrix | GET, POST | `/risk-matrix/cells` | List or create matrix cells. |
| Risk Matrix | GET, PATCH | `/risk-matrix/cells/{matrix_cell_id}` | Read or update a matrix cell. |
| Risk Matrix | POST | `/risk-matrix/cells/{matrix_cell_id}/archive` | Archive a matrix cell. |
| Risks | GET, POST | `/risks` | List risks or create a draft risk. |
| Risks | GET, PATCH | `/risks/{risk_record_id}` | Read or update a risk. |
| Risks | GET | `/risks/{risk_record_id}/detail` | Read the authorized risk detail view. |
| Risks | POST | `/risks/{risk_record_id}/submit` | Submit a risk for committee workflow. |
| Risk Assessments | GET, POST | `/risk-assessments` | List or create an initial/residual assessment. |
| Risk Assessments | GET, PATCH | `/risk-assessments/{risk_assessment_id}` | Read or update an assessment. |
| Risk Actions | GET, POST | `/risk-actions` | List or create a mitigation action. |
| Risk Actions | GET, PATCH | `/risk-actions/{risk_action_id}` | Read or update an action. |
| Risk Actions | POST | `/risk-actions/{risk_action_id}/complete` | Complete an action. |
| Risk Decisions | GET, POST | `/risk-decisions` | List or record committee decisions. |
| Risk Decisions | GET | `/risk-decisions/{risk_decision_id}` | Read a decision. |
| Audit Logs | GET | `/audit-logs` | Query audit records. |
| Audit Logs | GET | `/audit-logs/{audit_log_id}` | Read an audit record. |
| Reports | POST | `/reports/risk-dossiers/{risk_record_id}` | Generate and track a DOCX risk dossier. |
| Reports | GET | `/reports` | List generated reports. |
| Reports | GET | `/reports/{generated_report_id}` | Read generated-report metadata. |
| Reports | GET | `/reports/{generated_report_id}/download` | Download the generated DOCX file. |

## Main MVP workflow

Use the following happy path as a frontend integration sequence. Requests that
change workflow state should send the Bearer token of the acting user.

1. **Log in** — `POST /auth/login` with `email` and `password`; expect HTTP 200
   with a JWT and user payload.
2. **Confirm the session** — `GET /auth/me`; expect HTTP 200 with the current
   user.
3. **Create a risk** — `POST /risks` with at least `problem_description` and
   `domain`; expect HTTP 201 and a draft risk record with its UUID.
4. **Create the initial assessment** — `POST /risk-assessments` with
   `risk_record_id`, `assessment_type: "INITIAL"`, `severity_level_id`, and
   `likelihood_level_id`; expect HTTP 201 with matrix-calculated fields.
5. **Submit the risk** — `POST /risks/{risk_record_id}/submit`, optionally with
   `reason`; expect HTTP 200 and an updated workflow status.
6. **Create a mitigation action** — `POST /risk-actions` with `risk_record_id`,
   `title`, and optionally `action_owner_user_id`, `description`, and
   `due_date`; expect HTTP 201.
7. **Complete the action** — `POST /risk-actions/{risk_action_id}/complete`
   with optional `completion_notes`; expect HTTP 200 with a completed action.
8. **Create the residual assessment** — `POST /risk-assessments` with
   `assessment_type: "RESIDUAL"` and the same matrix ID pair pattern; expect
   HTTP 201.
9. **Record the committee decision** — `POST /risk-decisions` with
   `risk_record_id`, `committee_id`, `decision_type`, and `decision_text`.
   Use `ACCEPT_RESIDUAL_RISK` when an authorized MIDDLE or HIGH committee
   accepts residual risk; expect HTTP 201 and the resulting risk workflow
   state.
10. **Read the risk detail** — `GET /risks/{risk_record_id}/detail`; expect the
    authorized consolidated detail response.
11. **Generate the dossier** — `POST /reports/risk-dossiers/{risk_record_id}`;
    `output_dir` is optional. Expect HTTP 201 with a generated report of type
    `RISK_DOSSIER_DOCX`.
12. **Download the dossier** — `GET /reports/{generated_report_id}/download`;
    expect the generated DOCX file through the protected download endpoint.
13. **Review audit history** — `GET /audit-logs`, optionally filtered by fields
    such as `entity_id`, `entity_type`, or `action`; expect authorized audit
    records.

## Risk matrix contract

Risk matrix levels and cells are configurable through `/risk-matrix`. The
default seed creates severity levels `S1`–`S5`, likelihood levels `L1`–`L5`,
risk levels `LOW`, `MEDIUM`, `HIGH`, and `EXTREME`, and 25 matrix cells.

For calculated assessments, provide both `severity_level_id` and
`likelihood_level_id`. The response includes `calculated_score`,
`calculated_risk_level_id`, `is_tolerable`, `requires_mitigation`, and
`requires_escalation` (as well as the selected IDs and matrix cell ID). Legacy
text fields `severity`, `likelihood`, and `risk_level` remain in the response
for compatibility and are populated from the calculation.

## Authorization summary

- Use Bearer authentication for protected endpoints.
- User, role, committee, committee-membership, and risk-matrix writes require
  an active member of a fixed MIDDLE or HIGH governance committee.
- A risk creator or owner controls risk updates and submission.
- An assigned action owner controls applicable action updates and completion.
- A decision actor must be an active member of the decision committee.
- Detailed-risk, report-generation/download, and audit-query access are
  authorization-controlled.

## Reports

Risk dossier reports use type `RISK_DOSSIER_DOCX`. Create one with
`POST /reports/risk-dossiers/{risk_record_id}`, discover tracked reports with
`GET /reports` or `GET /reports/{generated_report_id}`, and retrieve the file
with `GET /reports/{generated_report_id}/download`. Files are generated
server-side and downloaded through the protected download endpoint.
