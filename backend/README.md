# Backend

FastAPI backend skeleton for the Aviation Risk Management Tool.

## Requirements

- Python 3.11 or newer
- PostgreSQL for future database-backed features

## Create a Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Configure Environment

Copy `.env.example` to `.env` and adjust values as needed.

```powershell
Copy-Item .env.example .env
```

Default database URL:

```text
postgresql+psycopg://postgres:postgres@localhost:5432/aviation_risk_management
```

## Run Tests

Run from the `backend/` directory:

```powershell
pytest
```

## Run Locally

Run from the `backend/` directory:

```powershell
uvicorn app.main:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"aviation-risk-management-tool"}
```

## Bootstrap a Development Database

Run database migrations first, if applicable, then run this command from the
`backend/` directory:

```powershell
python -m app.cli bootstrap-admin --email admin@example.com --display-name "Admin User" --password "ChangeMe123!"
```

The command creates or ensures the default governance committees and roles,
creates or reuses the supplied admin user, and assigns that user to the Risk
Management Committee. It is idempotent and intended for controlled
backend/server-side initialization only; it is not a public API endpoint.
The password option is optional for now but recommended. It is securely hashed
before storage; plaintext passwords are never stored.

## Authentication

Bootstrap an admin with a password, then send `POST /auth/login` with:

```json
{"email": "admin@example.com", "password": "ChangeMe123!"}
```

Use the returned access token on protected requests:

```text
Authorization: Bearer <access_token>
```

Use `GET /auth/me` with the same Authorization header to retrieve the current
`UserRead` payload. This supports frontend session restore and token validation.

`X-User-Id` remains a temporary MVP fallback and will be removed later.
The bundled JWT secret is development-only. Production deployments must set
`JWT_SECRET_KEY` to a private secret of at least 32 bytes for HS256.
