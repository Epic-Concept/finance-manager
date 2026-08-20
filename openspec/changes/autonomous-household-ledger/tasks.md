# Implementation Plan

This is a design-first change. Slice 0 is this OpenSpec + ADR. Do not implement the current `add-classification-cockpit` transaction firehose while these slices are open.

TDD for every code slice. Impact-analyze symbols before editing them (`RuleGatherer`, `DbRuleSource`, `ShadowLearner`, `TransactionClusteringService`, `RuleValidationService`, `ReviewService`).

## 1. Slice 0 — Product rethink (this PR)

- [x] 1.1 OpenSpec proposal, design, and capability deltas
- [x] 1.2 ADR-002 capturing ledger / CEL / cohort / ADHD decisions
- [ ] 1.3 Owner accepts or amends: CEL dialect, money-at-risk default, reprocess-vs-forward, cockpit redirect
- [ ] 1.4 Mark `add-classification-cockpit` blocked-on-redirect (cohort card) before any web implementation

## 2. Slice 1 — CEL rule runtime

Smallest blast radius; unblocks everything else. Shadow-compare to regex before cutover.

- [ ] 2.1 Spike `celpy` on ARM64-class Python: compile/eval, `matches` + `(?i)`, ints, `&&`/`||`. Lock a dialect test file of the expressions we will emit.
- [ ] 2.2 Typed activation builder from `Transaction` (`amount_minor` = Numeric × 10^4). Tests for sign, scale, missing merchant/account.
- [ ] 2.3 CEL evaluator: compile-once, eval-many, skip invalid, log skip. No DB writes.
- [ ] 2.4 Change `RuleGatherer` / `RulePattern` to evaluate CEL; first true wins. Impact: gatherer tests, engine e2e, factory. **Keep emitting Evidence only.**
- [ ] 2.5 Migrator: regex and `description =~ "..."` → `txn.description.matches("...")`. Idempotent. Dry-run parity vs old regex gatherer on fixtures + a captured live-rule sample.
- [ ] 2.6 Generalize `RuleValidationService` to CEL dry-run (TP / also-match / labelled FP / conflicts). Retire `=~` extraction as the primary path.
- [ ] 2.7 Wire `DbRuleSource` + learner promotion + bootstrap `suggested_pattern` to write CEL. Update `InteractiveRefinementService` prompt to CEL (escape hatch, not default UX).
- [ ] 2.8 Tests: gatherer, migration parity, invalid skip, amount constraint, account constraint, priority. mypy --strict / ruff / black.

## 3. Slice 2 — Cohort discovery

- [ ] 3.1 Hierarchical clustering stages A–E on residual transactions (fixed amount, sign+account, merchant token, cadence, leftover). Keep existing first-token service as stage C.
- [ ] 3.2 Sequential covering loop: propose → dry-run → specialize/split → yield cohort. No rule writes without confirmation.
- [ ] 3.3 Template CEL synthesizer (escaped key, sign, account, exact amount, day-of-month). Tests that subscriptions separate from variable tickets.
- [ ] 3.4 LLM CEL synthesizer only on template failure; structured output; compile+dry-run or discard.
- [ ] 3.5 Replace bootstrap CLI proposals with cohorts (CEL + dry-run counts + coverage). Same confirm/skip semantics.
- [ ] 3.6 Shadow learner proposes CEL (not `re.escape(merchant_key)`). Still ≥1 human confirmation, no split caching except exact recurring.
- [ ] 3.7 Tests: residual shrinks on confirm, polluted token splits, template-without-LLM path, invalid LLM discarded.

## 4. Slice 3 — Ledger postings

- [ ] 4.1 Models: `pockets`, mapping from `account_name`, `journal_entries`, `postings` (minor units, signed, pocket xor nominal). Alembic on `finance` schema.
- [ ] 4.2 Auto-create pockets from distinct `account_name` values; Internal Transfer and P&L nominals stay categories.
- [ ] 4.3 Poster: decision → balanced entry (spend / income / split / transfer shapes). Exact zero sum. Tests per shape.
- [ ] 4.4 Hook poster into auto-apply and review resolve. Reclassify reverses then posts.
- [ ] 4.5 Reprocess command: rebuild postings from confirmed/auto-applied decisions after CEL cutover. Idempotent.
- [ ] 4.6 Read API for spend excluding transfers. Do not use `transaction_categories` as source of truth for new surfaces.
- [ ] 4.7 Tests: balance invariant, transfer-not-spend, split sums, reverse-on-reclassify.

## 5. Slice 4 — Autonomous review policy

- [ ] 5.1 Money-at-risk cap in config; interrupt-now vs queue-only vs silent. Large known merchant exception (history/rule) vs unknown.
- [ ] 5.2 Review list groups pending decisions into cohorts using slice 2; singletons only below min size.
- [ ] 5.3 Resolve-cohort endpoint: confirm/change/skip → mint rule + post matches. Skip leaves the cohort.
- [ ] 5.4 Cold-start guard: refuse a full classify-to-per-row-review when residual is huge and no cohorts have been offered.
- [ ] 5.5 Nightly job: sync → classify (cheap gatherers) → discover cohorts → learn. No extra daily ping.
- [ ] 5.6 Tests: small unknown queued, large unknown interrupt-now, 47 Tesco → 1 cohort, skip-is-idempotent.

## 6. Slice 5 — Quiet Ledger UI (redirected cockpit)

Depends on slices 2 and 4. Reuse design tokens from `add-classification-cockpit`; change the payload.

- [ ] 6.1 Shell + tokens + primitives as previously specified (Card, Button, TierMark, LedgerTable, StatLine)
- [ ] 6.2 Cohort focus card: samples, CEL, dry-run counts, confirm/change/split/skip, `c/e/s`
- [ ] 6.3 Same card for bootstrap and daily queue; coverage bar; singleton residual card as fallback
- [ ] 6.4 Overview: coverage, auto-apply rate, **cohort** depth, CEL rules table
- [ ] 6.5 Deploy web on gb10; live-confirm one real cohort; document the weekly ritual in the ops runbook

## Deferred (explicit)

- Offsetting-movement transfer gatherer (multi-txn; not CEL)
- Budget envelopes / net-worth charts (queries on postings)
- DSPy/GEPA gatherer optimization
- Outlook/M365 mailbox
- Multi-user auth
- Implementing per-transaction cockpit queues as the default
