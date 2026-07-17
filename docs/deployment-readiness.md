# Deployment Readiness Guide

## Purpose

This guide prepares the Aviation Risk Management Tool for safer deployment readiness. It documents Production Configuration, Environment Hardening, health checks, and operator checklists. It does not deploy the application and does not replace company IT, cybersecurity, data protection, or airworthiness approval.

## Environments

- `development`: local developer environment with local services and permissive local CORS.
- `test`: automated or isolated test runs. SQLite and test-only settings are acceptable here.
- `production`: deployed operational environment. Startup safety validation rejects unsafe configuration.

## Backend Environment Variables

| Variable | Required in Production | Example | Notes |
| --- | --- | --- | --- |
| `ENVIRONMENT` | Yes | `production` | Must be `development`, `test`, or `production`. |
| `DATABASE_URL` | Yes | `postgresql+psycopg://risk_user:strong_password@db.example.com:5432/risk_db` | Production must use PostgreSQL, not SQLite or local `postgres:postgres` credentials. |
| `JWT_SECRET_KEY` | Yes | `replace-with-a-long-random-secret-at-least-32-characters` | JWT Secret must be unique, private, and at least 32 characters. Do not commit it. |
| `JWT_ALGORITHM` | Yes | `HS256` | Keep aligned with token verification. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | `60` | Set according to company security policy. |
| `ENABLE_X_USER_ID_AUTH_FALLBACK` | Yes | `false` | Development Authentication Fallback must be disabled in production. |
| `CORS_ALLOWED_ORIGINS` | Yes | `https://risk-tool.example.com` | CORS Allowed Origins must be explicit production frontend origins. Avoid wildcards and localhost. |
| `ALLOW_LOCALHOST_CORS_IN_PRODUCTION` | No | `false` | Only set `true` for exceptional controlled testing. |
| `FRONTEND_BASE_URL` | Yes | `https://risk-tool.example.com` | Public frontend URL used in configuration and operator documentation. |
| `BACKEND_BASE_URL` | Yes | `https://risk-tool-api.example.com` | Public backend API URL. |
| `EVIDENCE_STORAGE_DIR` | Yes | `/var/lib/aviation-risk/evidence_uploads` | Evidence Storage path for uploaded evidence metadata/files. Ensure backup and access controls. |
| `GENERATED_REPORTS_DIR` | Yes | `/var/lib/aviation-risk/generated_reports` | Generated Reports path for controlled exports and DOCX reports. Ensure retention rules. |
| `MAX_EVIDENCE_UPLOAD_MB` | Yes | `25` | Maximum evidence upload size in MB. |
| `REQUIRE_SECURE_PRODUCTION_SETTINGS` | Yes | `true` | Production Configuration safety validation expects this to remain enabled. |

## Frontend Environment Variables

| Variable | Required in Production | Example | Notes |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | Yes | `https://your-risk-tool-api.example.com` | Backend API base URL compiled into the React app. |

## Production Configuration Checklist

- Strong JWT secret configured.
- Database points to production PostgreSQL.
- CORS restricted to real frontend HTTPS origin.
- Development auth fallback disabled.
- Evidence storage path configured.
- Generated reports path configured.
- Backup procedure defined.
- Data retention and archive policy reviewed before production/pilot use.
- Permission matrix reviewed before pilot/production use.
- Electronic approval concept reviewed before production use.
- Legal/investigation hold expectations defined.
- HTTPS/TLS handled by reverse proxy or hosting layer.
- Logs reviewed.
- Admin bootstrap password changed.
- Default test users disabled or removed.
- CI green before deployment.

## Backup and Restore Readiness

Backup and Restore procedure must be defined before production use. The backup scope must include the PostgreSQL database, evidence uploads, and generated reports. Restore must be tested in a non-production environment before relying on the procedure for SMS governance operations. See the [Backup and Restore Procedure](backup-and-restore.md).

## Data Retention and Archive Readiness

Review the [Data Retention and Archive Policy](data-retention-and-archive-policy.md) before production or pilot use. Confirm Retention Period ownership, Archive Policy expectations, Legal / Investigation Hold handling, and No Hard Delete expectations for governed SMS records.

## Permission Matrix Readiness

Review the [Permission Matrix and Access Control Policy](permission-matrix.md) before pilot or production use. Confirm Authority Level, Board of Origin, Fixed Governance Committee, export authorization boundary, archive/restore authority, and admin governance expectations.

## Electronic Approval Readiness

Review the [Electronic Approval / Signature Concept MVP](electronic-approval-concept.md) before production use. Confirm approval authority, Acknowledgement wording, Audit integrity expectations, and the limitation that this is Not a cryptographic digital signature.

## Local Development Startup

```powershell
docker compose up -d postgres

cd backend
Copy-Item .env.example .env
alembic upgrade head
python -m app.cli bootstrap-admin --email admin@example.com --display-name "Admin User" --password "ChangeMe123!"
python -m app.cli seed-default-risk-matrix
python -m app.cli seed-test-access-profiles --password ChangeMe123!
uvicorn app.main:app --reload
```

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

The frontend development server uses port `5174`. The backend uses port `8000`.

## Production Startup Checklist

- Install backend dependencies.
- Install frontend dependencies.
- Configure environment variables outside the repository.
- Run `alembic upgrade head`.
- Bootstrap or migrate the admin user securely.
- Start backend with the approved production ASGI server command.
- Build frontend.
- Serve frontend via approved web server or hosting platform.
- Configure HTTPS and CORS.

## Health Checks

- `GET /health`: basic Health Check for service availability.
- `GET /health/readiness`: safe readiness metadata for Environment Hardening and operational checks. It does not expose secrets, database URLs, passwords, or the full CORS origin list.

## Known Non-Production Features

- Dev bootstrap admin command.
- Seed test access profiles.
- Local fallback authentication setting.

## SMS Governance Note

The tool supports SMS governance workflows, evidence traceability, committee decisions, and audit preparation. Production deployment must still follow company IT, cybersecurity, data protection, and airworthiness governance requirements.
