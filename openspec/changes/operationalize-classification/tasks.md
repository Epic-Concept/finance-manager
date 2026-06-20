## 1. Azure connectivity spike

- [x] 1.1 Resolve how gb10 reaches the Azure SQL source despite a changing egress IP — RESOLVED: gb10 has a stable home egress IP `45.11.63.27`, already allowlisted by the Terraform-managed `AllowHome` firewall rule on the SQL server + SSL + Entra SP auth (see design Spike Results 1.1)
- [x] 1.2 Add the read-only Azure connection secret + config setting; verify a live SSL connection from gb10 — DONE. Source is **Azure SQL** `sqldb-home-automation` (schema `finance`), auth via Entra SP `finance-manager-gb10` (appId 82fdfa33…), provisioned in IaC (Epic-Concept/epic-concept-infra-platform#15 merged+applied: SQL MI + SP + secret→Key Vault `kv-epic-concept-mgt`). gb10 `.env` has AZURE_SQL_{TENANT_ID,CLIENT_ID,CLIENT_SECRET,SERVER,DATABASE}. DB user created by SID (`0x33FAFD82…`) + `db_datareader` (no Directory Readers needed). **Live-verified**: SP read `finance.bank_transactions` (4415 rows, 14 cols incl. transaction_id/synced_at/amount-decimal) from gb10 over SSL.

## 2. Transaction ingestion (Azure -> gb10)

- [ ] 2.1 Implement the incremental pull-sync: query source rows where `synced_at` > cursor, ordered, bounded per run
- [ ] 2.2 Implement idempotent upsert keyed by `transaction_id` -> `external_id` (skip/update existing)
- [ ] 2.3 Implement normalization (source columns -> canonical `Transaction`, exact-decimal amount)
- [ ] 2.4 Persist + advance the sync cursor only on success; leave unchanged on failure
- [ ] 2.5 Add a runnable sync entrypoint (CLI) suitable for scheduling
- [ ] 2.6 Tests: incremental fetch, idempotency, normalization, failure-leaves-cursor (pure logic with a fake source; one live backfill against Azure)

## 3. Classification runtime

- [ ] 3.1 Implement `DbHistorySource` (prior confirmed outcomes per merchant) + tests
- [ ] 3.2 Implement the engine factory: compose policy + gatherers (rules/history/web/llm/agentic-receipt) from config; omit unconfigured backends
- [ ] 3.3 Implement the daily classification job: classify new/unclassified transactions, persist decisions+splits+evidence, enqueue reviews; idempotent
- [ ] 3.4 Add a runnable classify entrypoint (CLI) for scheduling
- [ ] 3.5 Tests: factory composition, history source, daily-job idempotency (fakes); one live end-to-end on a small synced sample

## 4. Cold-start bootstrap

- [ ] 4.1 Seed the 117-category hierarchy on gb10 (Python seeder) incl. an internal-transfer category
- [ ] 4.2 Build the interactive bootstrap CLI: cluster -> show top clusters + LLM proposal + coverage -> operator confirms/corrects/skips
- [ ] 4.3 On confirm, create active rules via `apply_proposals`; support assigning the internal-transfer category to self/business/family clusters
- [ ] 4.4 Run the bootstrap on the real transactions to seed the initial rule cache
- [ ] 4.5 Tests: confirm-creates-rule, skip-creates-nothing, coverage reporting (fakes)

## 5. Review and learning loop

- [ ] 5.1 Review API: list pending review items (summary, proposed categorization, strength/reason, evidence)
- [ ] 5.2 Review API: resolve an item (confirm / reclassify / mark internal-transfer) -> apply categorization, leave the queue
- [ ] 5.3 Emit a human-confirmed learner observation on resolve (and for un-corrected auto-applies)
- [ ] 5.4 Scheduled learner run over accumulated observations -> promote stable rules (off the hot path)
- [ ] 5.5 Minimal review screen on the React skeleton (list + resolve)
- [ ] 5.6 Tests: list/resolve behavior, observation emission, promotion from confirmations

## 6. Scheduling & operation on gb10

- [ ] 6.1 Schedule the nightly pipeline (sync -> classify -> learn) via cron / systemd timer on gb10
- [ ] 6.2 Run the API as a long-lived service on gb10 (compose), reachable over Tailscale
- [ ] 6.3 Verify a full overnight cycle end-to-end on real data; document run/backup/restore ops
