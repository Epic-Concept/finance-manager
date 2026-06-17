# Deployment on gb10.local

The Finance Manager is self-hosted on `gb10.local`, co-located with the local
LLM so financial data and mailbox content never leave the host.

## Topology

| Component | Where | Notes |
|-----------|-------|-------|
| PostgreSQL | container `finance-manager-db` (`pgvector/pgvector:pg16`) | published on host port **5433** (host's 5432 is used by another service) |
| Local LLM | vLLM (`qwen-moe`, host port 8000) behind the `litellm` gateway (host port 4000) | already running on the host |
| API / Web | _not yet deployed_ — see "Application deployment" below | |

Host-local secrets live in `~/finance-manager/.env` (mode `600`, never committed).
On the host, the app connects to Postgres at `localhost:5433`.

## PostgreSQL container

Provisioned with:

```bash
docker run -d \
  --name finance-manager-db \
  --restart unless-stopped \
  -e POSTGRES_USER=finance \
  -e POSTGRES_PASSWORD=<secret> \
  -e POSTGRES_DB=finance \
  -p 5433:5432 \
  -v finance-manager-pgdata:/var/lib/postgresql/data \
  pgvector/pgvector:pg16
```

Data persists in the named volume `finance-manager-pgdata`. The `pgvector`
image is a superset of stock Postgres 16, leaving room for future embedding /
evidence-retrieval use without another migration.

## Migrations

From a checkout with `DATABASE_URL` pointing at the host Postgres:

```bash
cd apps/api
DATABASE_URL=postgresql+psycopg://finance:<secret>@gb10.local:5433/finance \
  alembic upgrade head
```

## Backup and restore

Backups use `pg_dump` in custom format (compressed, supports selective restore).

**Backup:**

```bash
docker exec finance-manager-db pg_dump -U finance -d finance -Fc -f /tmp/finance_backup.dump
docker cp finance-manager-db:/tmp/finance_backup.dump ~/finance-manager/backups/finance_$(date +%F).dump
```

**Restore** (into a fresh database, then verify before swapping):

```bash
docker exec finance-manager-db psql -U finance -d postgres -c "CREATE DATABASE finance_restore;"
docker cp ~/finance-manager/backups/<file>.dump finance-manager-db:/tmp/restore.dump
docker exec finance-manager-db pg_restore -U finance -d finance_restore /tmp/restore.dump
# verify, then promote finance_restore to the live database as needed
```

A dump→restore→verify round-trip has been confirmed working on this host.

> **Cadence:** schedule the backup command (e.g. via cron on the host) and keep
> recent dumps under `~/finance-manager/backups/`. Retention and off-host copies
> are an operational choice (see the migration change's open questions).

## Application deployment

The API connects to Postgres successfully (verified via `alembic` + the test
suite + a `uvicorn` smoke test reporting `database: connected`). Standing up the
API and web as long-running services on the host still needs a decision on
**ports and process supervision**, because the host is shared:

- Host port **8000 is taken** by the local LLM (`qwen-moe`), so the API must use
  a different host port (e.g. 8088).
- Choose container (compose) vs native/systemd supervision for the app processes.

Until that is decided, the database tier is live and the app runs on demand
against it.
