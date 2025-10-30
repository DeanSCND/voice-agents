# Archer Backend - Phase 1

FastAPI backend with Cartesia Line SDK integration for banking voice agent.

## Setup

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
poetry run alembic upgrade head

# Start server
poetry run uvicorn src.main:app --reload --port 8000
```

## Phase 1 Features

- Customer identity verification (2FA: account_last_4 + postal_code)
- Payment options calculation (full payment, settlement, payment plan)
- Payment processing (SMS link, bank transfer, payment plan)
- PostgreSQL persistence with SQLAlchemy async
- Alembic migrations
- Comprehensive test suite

## Testing

```bash
# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=src --cov-report=html
```
