# Operating the classification pipeline on gb10

The evidence-driven classifier runs on `gb10` as Docker containers on the
`finance-net` network. Transactions flow nightly from the upstream **Azure SQL**
(`sqldb-home-automation`) into the local canonical Postgres, are classified, and
low-confidence cases queue for human review; confirmations grow the rule cache.

## Topology

| Container | Role | Port |
|-----------|------|------|
| `finance-manager-api` | FastAPI app + the sync/classify/learn CLIs | 8088→8000 |
| `finance-manager-web` | React UI | 8089→80 |
| `finance-manager-db`  | Postgres (pgvector) canonical store | 5433→5432 |
| `llm-gateway` | local litellm gateway (qwen) | 4000 |

Secrets live only in `~/finance-manager/.env` (gitignored), injected into the
API container via `docker-compose.gb10.yml` (`env_file: ../.env`). It holds the
`AZURE_SQL_*` Entra service-principal credentials (read-only `db_datareader`).

## Deploy / update

```bash
# sync code to the gb10 checkout, then rebuild + restart the API
rsync -az --exclude .venv --exclude __pycache__ --exclude .env \
  apps/api/ mfalkiewicz@gb10:~/finance-manager/app/apps/api/
cd ~/finance-manager/app
docker compose -f docker-compose.gb10.yml --env-file ~/finance-manager/.env up -d --build api
```

## Migrations

The image ships only `src/`, so run Alembic via a one-off container that mounts
the checkout (which has `alembic/`):

```bash
docker run --rm --network finance-net -v ~/finance-manager/app/apps/api:/work -w /work \
  --env-file ~/finance-manager/.env finance-manager-api \
  sh -c 'DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@finance-manager-db:5432/$DB_NAME alembic upgrade head'
```

## First-run / cold start (do this once, before relying on nightly classify)

There is **no reprocessing after rule changes**, so warm the rule cache *before*
the first full classify, or day one is ~100% review.

```bash
# 1. seed the category hierarchy (incl. Internal Transfer)
docker exec finance-manager-api python -m finance_api.scripts.seed_categories

# 2. backfill transactions from Azure SQL
docker exec finance-manager-api python -m finance_api.scripts.sync_transactions

# 3. bootstrap rules INTERACTIVELY (cluster -> LLM proposal -> you confirm).
#    Needs the local LLM; pass its gateway + key inline (key = llm-gateway master key).
docker exec -it \
  -e LITELLM_BASE_URL=http://172.17.0.1:4000/v1 \
  -e LITELLM_API_KEY=<llm-gateway master key> \
  finance-manager-api python -m finance_api.scripts.bootstrap_rules --top-n 100

# 4. classify the backlog with the now-warm rules
docker exec finance-manager-api python -m finance_api.scripts.classify_transactions
```

> The nightly classify deliberately runs **without** the LLM gatherers (fast
> rules/history path). Enable them in steady state by adding `LITELLM_BASE_URL`
> /`LITELLM_API_KEY` (and `BRAVE_API_KEY`, `GMAIL_IMAP_*`) to `~/finance-manager/.env`
> once the backlog is bootstrapped — then only genuinely-new merchants hit the LLM.

## Nightly pipeline (scheduled)

`~/finance-manager/nightly.sh` runs `sync -> classify -> learn`, scheduled at
05:30 via cron, logging to `~/finance-manager/nightly.log`:

```
30 5 * * * /home/mfalkiewicz/finance-manager/nightly.sh >> /home/mfalkiewicz/finance-manager/nightly.log 2>&1
```

Manual run: `~/finance-manager/nightly.sh`. Tail logs: `tail -f ~/finance-manager/nightly.log`.

## Review loop

- List pending: `GET http://gb10:8088/api/v1/reviews`
- Resolve one: `POST http://gb10:8088/api/v1/reviews/{decision_id}/resolve {"category_id": N}`
  (confirm / reclassify / mark internal-transfer — pass the chosen category id).

Resolving marks the decision `confirmed`; the scheduled learner promotes stable,
confirmed merchants to rules so they auto-apply next time.

## Backup / restore

```bash
# backup the canonical store
docker exec finance-manager-db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > ~/finance-manager/finance_$(date +%F).dump

# restore
cat <backup>.dump | docker exec -i finance-manager-db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Azure SQL is the upstream source of truth for raw transactions; the sync is
idempotent (keyed by `transaction_id`), so a lost local store can be rebuilt by
resetting the `sync_state` cursor and re-running the sync.
```
