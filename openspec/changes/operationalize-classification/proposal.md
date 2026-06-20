## Why

The evidence-driven classification engine is built and live-verified, but it does not yet run on its own: there is no transaction ingestion, no scheduled classification run, no way to bootstrap the rule cache without drowning in reviews, and no surface to confirm reviews or feed confirmations back to the learner. This change makes the system **operational end-to-end** on `gb10.local`: transactions flow in nightly from the existing Azure SQL feed, get classified, low-confidence cases queue for review, and human confirmations grow the deterministic rule cache so the system gets cheaper and more accurate over time.

## What Changes

- **NEW** Nightly **pull-sync** from the upstream Azure SQL (already updated each evening) into the canonical gb10 store: incremental by `synced_at` cursor, idempotent by `transaction_id`, normalized into the canonical `Transaction`. Pull-based (gb10 polls), preserving local-first — only already-cloud-resident transaction data is read; all classification, evidence, and email processing stay on gb10.
- **NEW** A **classification runtime**: a factory that composes the real engine (policy + all gatherers — rules, history, web-lookup/Brave, LLM-inference, agentic-receipt/Gmail) from configuration, plus the missing `DbHistorySource` adapter, and a **daily orchestration job** that classifies newly-synced unclassified transactions, persists decisions/splits/evidence, and enqueues review items.
- **NEW** A **cold-start rule bootstrap** CLI: cluster real transactions, the LLM proposes a category per cluster, the human confirms in bulk, and confirmed clusters become rules (incl. a `Transfer/Internal` category for intra-family/business movements that are not spend). Seeds the 117-category hierarchy and the initial rule cache.
- **NEW** A **review-and-learning loop**: an API to list and resolve review-queue items (confirm / reclassify / mark-transfer), and the wiring that turns confirmed outcomes into learner observations so the shadow learner promotes stable rules on a schedule.
- Adds a scheduled-job mechanism on gb10 (cron / systemd timer) to run the nightly sync → classify → learn pipeline.

## Capabilities

### New Capabilities
- `transaction-ingestion`: Incremental nightly pull-sync of transactions from the upstream Azure SQL into the gb10 store — cursor/checkpointing, idempotent upsert, normalization to the canonical model, and scheduling.
- `classification-runtime`: Production composition of the classification engine (engine factory + config for gatherers/mailboxes/categories), the `DbHistorySource` adapter, and the daily orchestration job that classifies new transactions and records decisions + review items.
- `rule-bootstrap`: Cold-start bootstrapping of the rule cache from unlabelled data — cluster → LLM-propose-per-cluster → human-confirm → seed rules; plus seeding categories and handling intra-family/business transfers.
- `review-and-learning`: The human review surface (list/resolve review items) and the confirmation → learner → rule-promotion loop that improves coverage over time.

### Modified Capabilities
<!-- None: this builds on the completed add-evidence-driven-classification capabilities without changing their requirements. -->

## Impact

- **Affected code:** new `finance_api/ingestion/` (sync), `finance_api/classification/` (engine factory, `DbHistorySource`), new orchestration entrypoints/scripts, a review router under `finance_api/routers/`, and the React skeleton in `apps/web/` for the review surface.
- **Dependencies:** a read-only Azure SQL connection reachable from gb10 over SSL, authenticated with an **Entra service principal** (`finance-manager-gb10`, token auth via `azure-identity` + `pyodbc`/`msodbcsql18`; `db_datareader`) — provisioned in IaC (epic-concept-infra-platform). Reuses the local LLM (gb10), Brave, and Gmail IMAP already wired.
- **Data/config:** new sync-cursor state and Azure connection secret (gitignored); categories + bootstrapped rules seeded on gb10.
- **Operations:** scheduled jobs on gb10; the app run as a long-lived service; depends on the deferred `gb10.local` app deployment (compose) from the migrate-to-postgres change.
- **Out of scope (deferred):** household Outlook/M365 mailbox (needs Azure OAuth/admin consent), a dedicated transfer-detection subsystem (handled here only as a bootstrap category), full reprocessing-after-rule-change, and the DSPy/GEPA evaluation/optimization loop.

## Open Questions

- ~~**Azure connectivity from a mobile gb10**~~ — RESOLVED: gb10 has a stable home egress IP (`45.11.63.27`), already allowlisted by the Terraform-managed `AllowHome` firewall rule on the Azure SQL server. Auth is an Entra service principal (token), codified in IaC. See design Spike Results 1.1.
- **Daily-job shape:** single nightly batch vs. continuous classify/learn; the agentic receipt hunts are slow (~tens of seconds each), so a night's worth of new unknowns may need queueing/concurrency.
