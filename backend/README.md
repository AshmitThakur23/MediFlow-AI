# MediFlow AI Backend

This directory contains the academic-MVP backend foundation and local synthetic
API demonstration. It includes SQLAlchemy models, authentication, tenant
isolation, patient/encounter, provenance, clinical-history, catalogue,
prescription, document metadata, and SQLite demo startup.

## Setup

From the MediFlow-AI repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
```

For the local synthetic showcase, `.env` uses SQLite:

```text
DATABASE_URL=sqlite+pysqlite:///./mediflow.db
```

Do not commit real credentials or real patient data.

## Run

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API health: `http://127.0.0.1:8000/api/v1/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

The startup process creates SQLAlchemy tables in SQLite and seeds one synthetic
doctor, one synthetic hospital, and one synthetic patient.

## Alembic

The migration environment is configured, but no clinical or application tables are implemented yet.

```powershell
alembic revision --autogenerate -m "initial foundation"
alembic upgrade head
```

Do not create migrations for clinical tables until their implementation is approved in a later task.
