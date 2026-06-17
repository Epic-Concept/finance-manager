## Context

The system is consolidating onto a single self-hosted machine, `gb10.local`, where the local LLM already lives. Co-locating the data store there keeps financial data and raw mailbox content entirely on-host, which is the project's privacy boundary. The current persistence layer is Microsoft SQL Server via `mssql+pyodbc`, run from `docker-compose.yml`, with 9 Alembic migrations. Models use generic SQLAlchemy types (String, Integer, DateTime, Boolean, Text, Numeric) under a `finance` schema, so the only clearly dialect-specific code found is the T-SQL schema creation in `002_create_finance_schema.py` (`sys.schemas` + `EXEC`). There is no production data to preserve yet, so this is a platform swap rather than a data migration.

This change is a prerequisite for `add-evidence-driven-classification`, whose data-model work (categorization splits, evidence persistence) targets Postgres.

## Goals / Non-Goals

**Goals:**
- PostgreSQL as the data store, co-located with the app and LLM on `gb10.local`.
- A clean driver/URL swap (`mssql+pyodbc` → `postgresql+psycopg`) and dependency change (`pyodbc` → `psycopg`).
- Dialect-portable migrations that apply cleanly on a fresh Postgres database.
- A defined backup/restore procedure for the Postgres data.
- The existing test suite passing on Postgres.

**Non-Goals:**
- The classification core (separate change).
- Cloud/Azure deployment — the `infra/` Terraform stays deferred.
- Transferring existing rows (none worth preserving yet); a one-time export/import is only needed if local data must be kept.

## Decisions

### Decision: PostgreSQL over keeping SQL Server
Postgres is lighter to self-host, has no ODBC driver friction, and co-locates cleanly with the rest of the on-prem stack. SQL Server's licensing/footprint and the `pyodbc` + ODBC Driver 18 chain add operational weight with no benefit for a single-host local deployment. *Alternative considered:* SQLite — rejected because the schema uses a named `finance` schema and the app is a long-running multi-connection service where Postgres is a better fit; keeping it also eases any later multi-user expansion.

### Decision: `postgresql+psycopg` (psycopg 3) driver
Use psycopg 3 (`postgresql+psycopg`) as the SQLAlchemy driver. *Alternative considered:* `psycopg2` (mature but legacy) and `asyncpg` (async-only, more churn given the current sync repositories) — psycopg 3 is the current default and works with the existing sync SQLAlchemy 2.0 setup.

### Decision: Recreate schema, don't migrate rows
Since there is no production data, run the migration chain against a fresh Postgres database rather than building a SQL-Server→Postgres data transfer. This keeps the change small and low-risk. If any local dev data matters, a one-off `pg`-side import is done manually.

### Decision: Keep the `finance` schema
Retain the named `finance` schema (Postgres supports schemas), so model `__table_args__` and FKs remain unchanged. Only the schema *creation* SQL changes.

## Risks / Trade-offs

- **Hidden dialect-specific SQL beyond the schema migration** → Mitigation: audit all 9 migrations and run the full chain on a fresh Postgres DB in CI before merge; the grep found only the T-SQL schema creation, but verify by execution, not inspection alone.
- **Type/identity differences (e.g. autoincrement, default timestamps)** → Mitigation: rely on SQLAlchemy's portable types; verify generated DDL and that `autoincrement` PKs and `datetime.utcnow` defaults behave on Postgres.
- **Test suite assumptions tied to SQL Server** → Mitigation: point the test database at Postgres and fix any dialect-coupled assertions; treat a green suite on Postgres as the acceptance bar.
- **Single-host availability** → co-locating everything on `gb10.local` means one machine is a single point of failure. Mitigation: the defined Postgres backup/restore procedure; acceptable for a household-scale local-first system.
- **Connection/credential management on the host** → Mitigation: keep `DATABASE_URL` and Postgres credentials in local env/secrets on `gb10.local`, not in the repo.

## Migration Plan

1. Add the Postgres driver dependency (`psycopg[binary]`) and remove `pyodbc` from `pyproject.toml`.
2. Update `DATABASE_URL` defaults in `config.py` and `.env.example` to `postgresql+psycopg://...@gb10.local:5432/<db>`.
3. Rewrite `002_create_finance_schema.py` to `CREATE SCHEMA IF NOT EXISTS finance`; audit the other migrations for dialect-specific SQL.
4. Replace the `mssql` service in `docker-compose.yml` with a `postgres` service (image, healthcheck, volume, port 5432).
5. Run `alembic upgrade head` against a fresh Postgres database; confirm all tables/indexes are created.
6. Run the full pytest suite against Postgres; fix any dialect-coupled tests.
7. Define and document the Postgres backup/restore procedure on `gb10.local`.
8. Deploy the app + Postgres on `gb10.local`, co-located with the LLM.

Rollback: the change is isolated to config, deps, one migration, and compose; reverting those restores the SQL Server setup. Since no rows are transferred, rollback carries no data-loss risk.

## Open Questions

- Postgres deployment shape on `gb10.local`: container (compose) vs native service — and how the LLM and app processes are supervised alongside it.
- Backup cadence and retention for the household data, and where backups are stored (still on-host vs an external drive).
- Whether any existing local dev data needs a one-time export/import, or a fresh schema is acceptable.
