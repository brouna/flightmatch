.PHONY: migrate run worker beat test ui

# Run database migrations
migrate:
	alembic upgrade head

# Start API server (dev)
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker
worker:
	celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
beat:
	celery -A app.tasks.celery_app beat --loglevel=info

# Run tests (requires test DB to be running)
test:
	pytest tests/ -v

# Run only unit tests (no DB needed)
test-unit:
	pytest tests/test_email.py tests/test_matching.py::test_heuristic_scorer tests/test_matching.py::test_feature_engineering -v

# Build UI
ui:
	cd ui && npm install && npm run build

# Dev UI (with hot reload)
ui-dev:
	cd ui && npm run dev

# Import sample historical data
import-sample:
	python3 scripts/import_historical.py data/sample_flights.csv

# Train ML model
train:
	python3 -m ml.train

# Show model stats
evaluate:
	python3 -m ml.evaluate
