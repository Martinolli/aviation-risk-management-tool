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
