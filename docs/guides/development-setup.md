# Development Setup

This guide walks through setting up a local development environment for the Finance Manager application.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (required for database and full stack development)

The API connects to PostgreSQL via the `psycopg` driver, which ships its own
libpq in the binary wheel — no system database client or ODBC driver is needed.

## Quick Start (Docker Compose)

The fastest way to get started is using Docker Compose:

```bash
# Start all services (database, API, web)
docker-compose up

# Or start in background
docker-compose up -d
```

This starts:
- PostgreSQL 16 on port 5432
- API on http://localhost:8000
- Web on http://localhost:80

## Database Setup

### Starting the Database

```bash
# Start only the database
make db-up

# Or using docker-compose directly
docker-compose up -d db
```

The database will be available at `localhost:5432` with:
- Username: `finance` (default, change via `DB_USER` env var)
- Password: `finance` (default, change via `DB_PASSWORD` env var)
- Database: `finance` (default, change via `DB_NAME` env var)

### Running Migrations

```bash
# Apply all migrations
make db-migrate

# Or manually
cd apps/api
alembic upgrade head
```

### Creating New Migrations

```bash
cd apps/api
alembic revision --autogenerate -m "description of change"
```

### Resetting the Database

```bash
# Destroys all data and recreates the database
make db-reset
```

## Backend Setup (Without Docker)

1. Start the database:
   ```bash
   make db-up
   ```

2. Navigate to the API directory:
   ```bash
   cd apps/api
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

5. Set up environment:
   ```bash
   cp ../../.env.example .env
   ```

6. Run migrations:
   ```bash
   alembic upgrade head
   ```

7. Run tests:
   ```bash
   pytest
   ```

8. Start the development server:
   ```bash
   uvicorn finance_api.main:app --reload
   ```

The API will be available at http://localhost:8000.

## Frontend Setup

1. Navigate to the web directory:
   ```bash
   cd apps/web
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run tests:
   ```bash
   npm test
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

The web app will be available at http://localhost:5173.

## Using Make

From the repository root:

```bash
# Install all dependencies
make install

# Run all tests
make test

# Run all linters
make lint

# Format code
make format

# Database commands
make db-up        # Start database
make db-down      # Stop database
make db-migrate   # Run migrations
make db-reset     # Reset database

# Start all services
make run
```

## Environment Variables

Copy `.env.example` to `.env` and customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | See .env.example |
| `DB_USER` | Database user | `finance` |
| `DB_PASSWORD` | Database password | `finance` |
| `DB_NAME` | Database name | `finance` |
| `DB_PORT` | Database port | `5432` |
| `API_PORT` | API port | `8000` |
| `WEB_PORT` | Web port | `80` |

## IDE Configuration

### VS Code

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Terraform
- Docker

### PyCharm / WebStorm

1. Mark `apps/api/src` as Python source root
2. Mark `apps/web/src` as JavaScript source root
3. Configure Python interpreter to use the virtual environment

## Troubleshooting

### Database connection issues

1. Ensure Docker is running
2. Check the database is healthy: `docker-compose ps`
3. Verify Postgres is accepting connections: `docker exec finance-manager-db pg_isready -U finance`
4. Check connection string in `.env`

### API not starting

1. Ensure virtual environment is activated
2. Check that all dependencies are installed: `pip install -e ".[dev]"`
3. Verify Python version: `python --version` (should be 3.11+)
4. Ensure database is running and migrations are applied

### Frontend not connecting to API

1. Ensure the API is running on port 8000
2. Check the proxy configuration in `vite.config.ts`
3. Look for CORS errors in the browser console

### PostgreSQL container won't start

1. Check the container logs: `docker-compose logs db`
2. Ensure host port 5432 is free, or set `DB_PORT` to another port
3. If the data volume is corrupted, recreate it: `docker-compose down -v && docker-compose up -d db` (destroys local data)
