# Tasks: Add Local Development Database

## Section 1: Docker Compose Setup
- [x] Create `docker-compose.yml` with SQL Server 2022 service
- [x] Add API service configuration to docker-compose
- [x] Add Web service configuration to docker-compose
- [x] Configure health checks for SQL Server container
- [x] Add `.env.example` with default environment variables

## Section 2: Database Module
- [x] Add SQLAlchemy, Alembic, pyodbc to `pyproject.toml`
- [x] Create `apps/api/src/finance_api/db/__init__.py` module
- [x] Create `apps/api/src/finance_api/db/engine.py` with engine configuration
- [x] Create `apps/api/src/finance_api/db/session.py` with session factory
- [x] Create `apps/api/src/finance_api/db/base.py` with declarative base
- [x] Add database settings to pydantic-settings configuration

## Section 3: Alembic Setup
- [x] Initialize Alembic in `apps/api/` directory
- [x] Configure `alembic.ini` for SQL Server connection
- [x] Update `alembic/env.py` to use application settings
- [x] Create initial empty migration (baseline)

## Section 4: API Integration
- [x] Add database session dependency for FastAPI
- [x] Update health check endpoint to verify database connectivity
- [x] Add database connection test to existing tests

## Section 5: CI/CD Updates
- [x] Add SQL Server service container to CI workflow
- [x] Add ODBC driver installation step to CI
- [x] Add migration validation step to CI
- [x] Update CI to run tests with database connection

## Section 6: Developer Experience
- [x] Add database commands to Makefile (db-up, db-down, db-migrate)
- [x] Update `docs/guides/development-setup.md` with database instructions
- [x] Update `.gitignore` with database-related entries
- [x] Add `apps/api/README.md` database section
