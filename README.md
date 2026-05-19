# Luna Back

> Crypto wallet backend with TON blockchain integration and background sync.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5-37814A?logo=celery&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)

## Overview

REST API backend for a TON blockchain wallet application. Handles user wallets,
on-chain balance syncing, referral system, energy mechanics, and daily earnings
via background Celery workers.

## Key Features

- **TON blockchain integration** — wallet lookup, balance sync via TON API
- **Repository pattern** — generic `BaseSQLAlchemyRepository` with ABC interface; fully testable, swappable data layer
- **Background processing** — Celery workers sync on-chain balances asynchronously
- **Referral system** — multi-level referral tracking with reward distribution
- **Energy mechanics** — daily earning calculations and energy management
- **Withdrawal queue** — pending withdrawal management
- **12 test modules** — integration and unit tests across all core features

## Architecture

```
src/
  api/v1/         — versioned REST endpoints
  repositories/   — data access layer (ABC interfaces + SQLAlchemy impl)
  services/       — business logic
  models/         — SQLAlchemy models
  schemas/        — Pydantic schemas
  tasks/          — Celery background tasks
  interfaces/     — abstract base classes
  management/     — CLI commands
tests/            — integration and unit tests
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 + SQLModel, Alembic migrations |
| Background | Celery, Redis |
| Database | PostgreSQL |
| Monitoring | Sentry |
| Dependency management | Poetry |
| Infrastructure | Docker, Docker Compose |

## Quick Start

```bash
# Install dependencies
poetry install

# Apply migrations
alembic upgrade head

# Run API server
gunicorn src.main:app --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Run Celery worker (separate terminal)
celery -A src.tasks worker --loglevel=info
```

API docs: `http://localhost:8000/docs`

## License

MIT
