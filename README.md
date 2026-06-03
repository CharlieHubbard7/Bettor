# Bettor

A systematic sports betting edge-finding system built for paper trading and eventual
real-money deployment. See [`CLAUDE.md`](./CLAUDE.md) for the full architecture and the
source of truth for every design decision.

## Status

- **Phase 1 (complete):** Backend infrastructure, core analytics (no-vig, edge detection,
  CLV), odds ingestion with fixture fallback, FastAPI routes, and a seeded database.
- **Phase 2 (next):** React frontend against the live API.

## Quick start

```bash
# First-time setup
cp backend/.env.example backend/.env
# Edit backend/.env — add ODDS_API_KEY and generate a SECRET_KEY (openssl rand -hex 32)

# Start everything
docker-compose up --build

# In a separate terminal — run migrations and seed
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_demo_data.py
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## Local development without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .            # or: poetry install
# Tests run against in-memory SQLite — no Postgres required
pytest --cov=app/analytics --cov-report=term-missing
```
