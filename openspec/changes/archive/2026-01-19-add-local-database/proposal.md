# Proposal: Add Local Development Database

## Change ID
`add-local-database`

## Summary
Set up SQL Server 2022 in Docker for local development with Alembic migrations, docker-compose orchestration, and CI/CD integration for schema validation.

## Motivation
The Finance Manager application needs a database for development and testing. Currently there's no local database setup, making it impossible to develop data-dependent features. This change establishes the foundational database infrastructure that all future domain features will build upon.

## Scope

### In Scope
- SQL Server 2022 Docker container configuration
- docker-compose for local development orchestration (API + Web + Database)
- Alembic migration framework integration with FastAPI
- SQLAlchemy as the ORM layer
- CI/CD pipeline update to spin up database and run migrations
- Empty initial schema (tables will be added in future changes)

### Out of Scope
- Domain table definitions (Accounts, Transactions, etc.) - future changes
- Production database provisioning (Azure SQL)
- Database backup/restore procedures
- Performance tuning or indexing strategies

## Impact Analysis

### Files Created
- `docker-compose.yml` - Local development orchestration
- `apps/api/src/finance_api/db/` - Database module (engine, session, base)
- `apps/api/alembic/` - Alembic migrations directory
- `apps/api/alembic.ini` - Alembic configuration

### Files Modified
- `apps/api/pyproject.toml` - Add SQLAlchemy, Alembic, pyodbc dependencies
- `.github/workflows/ci.yml` - Add database service and migration step
- `.gitignore` - Add Alembic and database-related ignores
- `Makefile` - Add database-related commands

### Dependencies Added
- `sqlalchemy>=2.0` - ORM and database toolkit
- `alembic>=1.13` - Database migrations
- `pyodbc>=5.0` - SQL Server driver
- SQL Server 2022 Docker image (`mcr.microsoft.com/mssql/server:2022-latest`)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQL Server container requires 2GB RAM | Medium | Dev machines may struggle | Document minimum requirements, provide memory config |
| ODBC driver compatibility issues | Low | Blocks development | Use well-tested pyodbc version, document setup steps |
| CI container startup time | Medium | Slower CI builds | Use health checks with reasonable timeouts |

## Success Criteria
1. `docker-compose up` starts SQL Server, API, and Web containers
2. `alembic upgrade head` runs without errors (empty migration)
3. API can connect to database and health check passes
4. CI pipeline successfully starts database service and validates migrations
5. Developer guide documents local setup process
