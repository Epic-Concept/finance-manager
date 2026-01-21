# Finance Manager API

FastAPI backend for the Finance Manager application.

## Quick Start

### Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Start database (from repo root)
make db-up

# Run migrations
alembic upgrade head

# Run tests
pytest

# Start development server
uvicorn finance_api.main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
apps/api/
├── alembic/              # Database migrations
│   ├── versions/         # Migration files
│   ├── env.py            # Alembic environment
│   └── script.py.mako    # Migration template
├── scripts/
│   └── sql/              # SQL seed scripts
│       └── seed_categories.sql
├── src/finance_api/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   ├── db/               # Database module
│   │   ├── base.py       # SQLAlchemy base
│   │   ├── engine.py     # Database engine
│   │   └── session.py    # Session factory
│   ├── core/             # Configuration & utilities
│   │   └── config.py     # Settings management
│   ├── routers/          # API route handlers
│   ├── services/         # Business logic
│   ├── repositories/     # Data access layer
│   ├── models/           # Pydantic/SQLAlchemy models
│   └── scripts/          # Python seed/utility scripts
│       ├── seed_data.py
│       └── seed_categories.py
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   └── test_main.py      # Main endpoint tests
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Database

### Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current
```

### Connection String

Set the `DATABASE_URL` environment variable:

```
DATABASE_URL=mssql+pyodbc://sa:Password123!@localhost:1433/master?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

### Seeding Data

#### Categories

Seed the category hierarchy (117 categories across 5 commitment levels):

```bash
# Copy SQL file to container and execute
docker cp apps/api/scripts/sql/seed_categories.sql finance-manager-db:/tmp/
docker exec finance-manager-db /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "Password123!" -C -d master \
  -i /tmp/seed_categories.sql
```

The categories follow a 5-level commitment model:
- **Level 0 (Survival)**: Non-negotiable expenses (housing, utilities, food basics)
- **Level 1 (Committed)**: Contractual obligations (insurance, communication)
- **Level 2 (Lifestyle)**: Adjustable quality-of-life expenses (personal care)
- **Level 3 (Discretionary)**: Easily reducible expenses (dining out, travel)
- **Level 4 (Future)**: Savings and investments (emergency fund, retirement)

#### Transactions and Purchases

Seed transaction and purchase data from Parquet files:

```bash
cd apps/api
PYTHONPATH=src DATABASE_URL="..." python -m finance_api.scripts.seed_data --data-dir /path/to/data
```

Options:
- `--clear`: Clear existing data before seeding
- `--transactions-only`: Only load bank transactions
- `--purchases-only`: Only load online purchases

## Code Quality

```bash
# Format code
black src tests
ruff check --fix src tests

# Type checking
mypy src

# Run all linters
ruff check src tests && black --check src tests && mypy src
```

## Docker

```bash
# Build image
docker build -t finance-manager-api .

# Run container
docker run -p 8000:8000 -e DATABASE_URL="..." finance-manager-api
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQL Server connection string | See above |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `false` |
