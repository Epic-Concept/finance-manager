## 1. Dependencies and configuration

- [x] 1.1 Add `psycopg[binary]` and remove `pyodbc` from `apps/api/pyproject.toml`
- [x] 1.2 Update `DATABASE_URL` default in `apps/api/src/finance_api/core/config.py` to `postgresql+psycopg://...`
- [x] 1.3 Update `.env.example` with the Postgres URL, port (5432), and credentials

## 2. Migrations

- [x] 2.1 Rewrite `alembic/versions/002_create_finance_schema.py` to use `CREATE SCHEMA IF NOT EXISTS finance` (remove `sys.schemas`/`EXEC` T-SQL)
- [x] 2.2 Audit all 9 migrations for other dialect-specific SQL/types and make them Postgres-portable
- [x] 2.3 Run `alembic upgrade head` on a fresh Postgres database and confirm all `finance`-schema tables and indexes are created
- [x] 2.4 Confirm `alembic downgrade base` runs cleanly on Postgres

## 3. Local stack

- [x] 3.1 Replace the `mssql` service in `docker-compose.yml` with a `postgres` service (image, healthcheck, volume, port 5432)
- [x] 3.2 Update the API service `DATABASE_URL` and any Dockerfiles to drop ODBC/SQL Server requirements
- [x] 3.3 Bring the stack up and verify the API connects and serves requests against Postgres

## 4. Tests

- [x] 4.1 Point the test database at Postgres and run the full pytest suite
- [x] 4.2 Fix any dialect-coupled test assertions (autoincrement PKs, timestamp defaults, decimal precision)
- [x] 4.3 Verify exact-decimal handling for monetary amounts on Postgres

## 5. Deployment on gb10.local

- [x] 5.1 Provision PostgreSQL on `gb10.local` and store credentials/`DATABASE_URL` in local secrets on the host
- [x] 5.2 Deploy the application on `gb10.local`, co-located with Postgres and the LLM, and confirm end-to-end operation with no cloud dependency
- [x] 5.3 Define and document a Postgres backup/restore procedure; verify a backup restores to a fresh instance with data intact
