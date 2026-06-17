## Why

The solution is moving to a **local-first, self-hosted** model on `gb10.local`, co-located with the local LLM so financial data and raw mailbox content never leave the host. The current stack uses Microsoft SQL Server (`mssql+pyodbc`, run via Docker), which is heavier than needed for a single-host deployment and is a poor fit for co-locating with the rest of the on-prem stack. Moving the data store to **PostgreSQL on `gb10.local`** simplifies operations, removes the ODBC/driver friction, and completes the local-first privacy story. This migration is a prerequisite for applying the evidence-driven classification change, whose data-model work assumes Postgres.

## What Changes

- **BREAKING** Replace Microsoft SQL Server with **PostgreSQL** as the primary data store.
- **BREAKING** Change the SQLAlchemy driver/URL from `mssql+pyodbc` to a Postgres driver (`postgresql+psycopg`), and replace the `pyodbc` dependency accordingly.
- Rewrite the schema-creation migration (`002_create_finance_schema.py`) from T-SQL (`sys.schemas` + `EXEC`) to portable Postgres (`CREATE SCHEMA IF NOT EXISTS finance`); audit the remaining 8 migrations for any other dialect-specific SQL.
- Replace the `mssql` service in `docker-compose.yml` with a `postgres` service; update healthcheck, volumes, and the `DATABASE_URL` default in config and `.env.example`.
- Define a **self-hosted deployment** on `gb10.local` where the application, PostgreSQL, and the LLM run on one machine, with a backup approach for the Postgres data.
- Verify the existing test suite (pytest, repository/integration tests) runs against Postgres.

## Capabilities

### New Capabilities
- `data-store`: PostgreSQL as the persistence platform — connection/driver, the `finance` schema, dialect-portable migrations, exact decimal handling, and parity of the existing data model on Postgres.
- `self-hosted-deployment`: The single-host `gb10.local` deployment model — app + PostgreSQL + LLM co-located, the privacy boundary (nothing leaves the host), and data backup/restore for Postgres.

### Modified Capabilities
<!-- None: prior persistence/deployment behavior was not captured as OpenSpec specs. -->

## Impact

- **Affected code:** `apps/api/src/finance_api/core/config.py` (DATABASE_URL), `apps/api/alembic/versions/002_create_finance_schema.py` (T-SQL → Postgres), audit of all `alembic/versions/*.py`, `apps/api/pyproject.toml` (`pyodbc` → `psycopg`), `docker-compose.yml`, `.env.example`, and any Dockerfiles.
- **Dependencies:** remove `pyodbc` (and the ODBC Driver 18 requirement); add a Postgres driver (`psycopg[binary]`).
- **Data:** this is a platform migration for a local-first system with no production data to preserve yet; the migration recreates the schema on Postgres rather than transferring rows. If any local data must be kept, a one-time export/import is required.
- **Operations:** Postgres now runs on `gb10.local`; backups, credentials, and connection config move to that host.
- **Sequencing:** prerequisite for `add-evidence-driven-classification` (its data-model tasks target Postgres).
- **Out of scope:** the classification core itself; cloud/Azure deployment (the `infra/` Terraform remains deferred).
