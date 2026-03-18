# FlightMatch

Humanitarian aviation pilot-mission matching service. Matches volunteer pilots to patient transport missions using hard rule filtering + LightGBM ML scoring.

## Quick Start

### 1. Prerequisites
```bash
apt install -y postgresql postgresql-client redis-server python3.13-venv nodejs npm
systemctl start postgresql redis-server
```

### 2. Databases
```bash
sudo -u postgres psql -c "CREATE USER flightmatch WITH PASSWORD 'flightmatch';"
sudo -u postgres psql -c "CREATE DATABASE flightmatch OWNER flightmatch;"
sudo -u postgres psql -c "CREATE USER flightmatch_test WITH PASSWORD 'flightmatch_test';"
sudo -u postgres psql -c "CREATE DATABASE flightmatch_test OWNER flightmatch_test;"
```

### 3. Python dependencies
```bash
pip3 install -r requirements.txt --break-system-packages
```

### 4. Run
```bash
make migrate   # Run Alembic migrations
make run       # Start API on http://localhost:8000
```

### 5. Admin UI (optional)
```bash
make ui-dev    # Start React dev server on http://localhost:5173
# or build for production:
make ui && make run   # Served from FastAPI at /
```

### 6. Celery (background tasks)
```bash
make worker    # Start Celery worker (calendar sync, email notifications)
make beat      # Start Celery Beat scheduler (hourly calendar sync)
```

## API

- Docs: http://localhost:8000/docs
- Auth: `X-API-Key: change-me-in-production` header (set `API_KEY` in `.env`)
- Base URL: `/api/v1`

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/missions/{id}/match` | Run match + send email notifications |
| `GET` | `/missions/{id}/pilots` | Get ranked pilot list (no persist) |
| `GET` | `/pilots/{id}/missions` | Get ranked missions for a pilot |
| `GET` | `/matches/respond?token=...` | Handle pilot email response link |
| `GET` | `/admin/stats` | Dashboard stats |
| `GET` | `/admin/rules` | List matching rules |
| `PATCH` | `/admin/rules/{id}` | Toggle/edit a rule (no redeploy needed) |
| `POST` | `/admin/import?file_path=...` | Import historical CSV |
| `POST` | `/admin/retrain` | Retrain LightGBM model |

## Matching Engine

1. **Hard rules** — filter pilots by aircraft capability, availability, distance (configurable via DB)
2. **ML scoring** — LightGBM binary classifier (predicts acceptance + completion)
3. **Cold start** — weighted heuristic when no trained model exists

## Testing

```bash
make test-unit    # Pure-Python tests (no DB needed) — 6 tests
make test         # Full test suite (requires test_postgres running)
```

## Project Structure

```
app/
  main.py               # FastAPI factory + lifespan (seeds default rules)
  config.py             # pydantic-settings (.env)
  models/               # SQLAlchemy ORM models
  schemas/              # Pydantic v2 schemas
  api/v1/               # Route handlers (pilots, aircraft, missions, matches, calendar, admin)
  matching/             # hard_rules, scorer, pipeline, feature_engineering, geo
  calendar_sync/        # Google OAuth2, Outlook MSAL, Apple CalDAV, Fernet encryption
  notifications/        # fastapi-mail + Jinja2 templates + itsdangerous response tokens
  tasks/                # Celery worker + beat (notifications, calendar sync, ML retrain)
ml/
  train.py              # Offline LightGBM training (80/20 time-split)
  evaluate.py           # Feature importances + metrics
  models/               # Serialized model artifacts (.joblib)
ui/                     # Vite + React + TanStack Query (7 pages)
scripts/
  import_historical.py  # CSV → historical_flights
data/
  sample_flights.csv    # Sample import data
alembic/
  versions/001_initial.py
```
