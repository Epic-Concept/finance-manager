## Context

`add-evidence-driven-classification` delivered the engine, gatherers, policy, persistence, learner, and bootstrap core — all live-verified against real qwen/Brave/Gmail/Postgres. But nothing runs unattended: there is no transaction ingestion, no scheduled classify run, no `DbHistorySource`, no operator review surface, and the rule cache starts empty. Transactions already land nightly in an upstream **Azure Postgres** (the user's existing pipeline); gb10 is the canonical local-first store for classification, decisions, and evidence. This change wires the daily loop: sync → classify → review → learn.

Constraints carried from the project: local-first on gb10, exact-decimal money, human-owned policy gate, gatherers behind Protocols, ≥1 human confirmation before rule promotion.

## Goals / Non-Goals

**Goals:**
- Nightly incremental ingestion from Azure Postgres into gb10 (cursor, idempotent, normalized).
- A production engine factory + `DbHistorySource` + a daily classification job.
- A cold-start bootstrap CLI that seeds rules cheaply (cluster → propose → confirm) and seeds categories incl. internal-transfer.
- A review surface + the confirmation→learner→promotion loop, scheduled.

**Non-Goals:**
- Outlook/M365 household mailbox (deferred — Azure OAuth/admin consent).
- A dedicated transfer-detection subsystem (handled here only as a bootstrap category).
- Reprocessing-after-rule-change and the DSPy/GEPA evaluation/optimization loop.
- A polished review UI beyond a functional surface on the existing React skeleton.

## Decisions

### Decision: Pull-sync, gb10 polls Azure
gb10 is mobile (Tailscale) with no stable ingress, so it polls Azure after the evening refresh rather than receiving a push. The source already stamps `synced_at` (cursor) and `transaction_id` (idempotency), so the sync is a thin incremental upsert, not a connector framework. *Alternative considered:* logical replication / FDW — rejected as heavyweight for a nightly batch.

### Decision: Azure is upstream source only; gb10 stays canonical
Transactions are read from Azure (already cloud-resident); all classification, decisions, evidence, and email/LLM processing remain on gb10. This keeps the privacy boundary intact — no new sensitive data leaves the host. Decisions are not written back to Azure.

### Decision: Single nightly batch pipeline
A scheduled job runs sync → classify-new → learn in sequence overnight. Matches a once-a-day source and avoids a long-running worker. Because agentic receipt hunts are slow, the classify step processes only *new, unclassified* transactions and may bound/queue the expensive gatherers; cheap gatherers (rules/history) resolve most volume once the cache is warm. *Alternative considered:* continuous workers — deferred until volume warrants.

### Decision: Bootstrap before first real run
Seed categories and run the cluster-bootstrap to create an initial rule cache before the first classify pass, so day-one isn't ~100% review. The bootstrap reuses the existing clustering + `ClusterCategoryProposer` + `apply_proposals`/`DbRuleSource`.

### Decision: Self-transfers as a bootstrap category, not a subsystem
Intra-family/business movements (≈7%: own name, business, family) are assigned an internal-transfer category during bootstrap. Proper offsetting-movement transfer detection is deferred.

### Decision: Review surface is functional-first
Expose list/resolve endpoints + a minimal screen on the React skeleton. The learning value comes from capturing confirmations, not from UI polish.

## Risks / Trade-offs

- **Azure connectivity from a mobile gb10** → its egress IP varies; Azure firewalls by IP. *Mitigation:* spike first — Tailscale exit node (fixed IP), Azure private endpoint + VPN, or SSL + strong-auth broad rule. Blocks the sync until resolved.
- **Cold-start review flood** → before the cache is warm, most transactions route to review. *Mitigation:* bootstrap top clusters first (≈74% coverage from ~100 clusters); promote aggressively-but-safely via the learner.
- **Slow agentic gatherers at batch scale** → a night of new unknowns × tens of seconds each. *Mitigation:* only classify new/unclassified; cap/queue expensive gatherers; rely on the rules fast-path post-bootstrap.
- **LLM mislabels self/business as spend** (seen: EPIC→Clothing, MARCEL→Groceries) → *Mitigation:* human confirmation is mandatory in bootstrap; internal-transfer category available.
- **Secret sprawl** (Azure conn string, on top of LLM/Brave/Gmail) → *Mitigation:* all in the gitignored host `.env`; never committed.

## Migration Plan

1. Resolve Azure connectivity (spike) and add the read-only Azure connection secret on gb10.
2. Build the ingestion sync (cursor/upsert/normalize) + a runnable entrypoint; backfill once, then nightly.
3. Build `DbHistorySource` + the engine factory; add the daily classify job.
4. Seed categories; run the bootstrap CLI to confirm top clusters → initial rules.
5. Build the review API + minimal UI; wire confirmations → observations; schedule the learner.
6. Schedule the nightly pipeline (sync → classify → learn) on gb10; run the app as a service.

Rollback: each piece is additive and independently disable-able (skip the schedule, skip the sync); no destructive changes to existing data.

## Open Questions

- Azure connectivity approach (the spike above) — fixed-IP exit vs private endpoint vs firewall rule.
- Daily-job concurrency/queueing for the slow agentic gatherers at real volume.
- Where review happens day-to-day (the React app vs a thin CLI) for the first iteration.
- Whether confirmed history alone (no rule yet) should auto-apply on the next occurrence, or always wait for learner promotion to a rule.
