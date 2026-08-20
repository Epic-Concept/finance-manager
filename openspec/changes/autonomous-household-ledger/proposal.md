## Why

The classifier is the product, and it already works as a gather/decide engine. What it does **not** yet do is run a household's books with almost no human effort. Today's rules are description regexes (after an earlier DSL was retired), clustering is "first token of the merchant name", review is one transaction at a time, and there is no ledger — only a category sticker on a bank row. That is still a bookkeeping app. For ADHD home finance it has to be the opposite: **the system keeps the books; the human audits exceptions, in groups, as rarely as possible.**

This change is a product rethink, not a rewrite of the evidence policy. Keep gather/decide, keep the local-first privacy boundary, keep the category tree. Change the *work unit*, the *rule language*, and the *books*.

## What Changes

- **NEW** A real **household ledger**: bank transactions stay immutable source facts; classification writes double-entry postings against asset/liability accounts and the existing category tree as **nominals**. Transfers, splits, and income are posting shapes, not special cases glued onto a single `category_id`.
- **NEW** **CEL (Common Expression Language)** as the stored rule language. A rule is a boolean expression over a typed transaction activation (`description`, `merchant`, `account`, signed amount in minor units, date fields). Matched rules still only emit `Evidence` — they do not become the policy. This restores what `rule_expression` was originally for, without bringing back the retired custom `rule-engine` DSL.
- **NEW** **Iterative cohort discovery**: sequential covering over residuals. Cluster → synthesize a CEL predicate → dry-run against the whole store (precision / false positives) → specialize or split → remove covered rows → repeat. The human confirms a *group*, not a row. One decision can classify dozens of transactions and mint a durable rule.
- **NEW** An **autonomous review policy** aimed at ADHD: interrupt budget of zero most days; weekly short ritual when a queue exists; immediate interrupt only for large-unknown / contested / money-at-risk. Skip is always safe. The primary review card is a cohort, not a single charge.
- **MODIFIED** `add-classification-cockpit` (Quiet Ledger) is **not implemented as specified**. Its design system and calm ritual stay; the work unit becomes the cohort. Building a 200-card transaction firehose would bake in the thing we are trying to escape.
- **MODIFIED** Rule gatherer, bootstrap, shadow learner, and rule validation switch from regex-as-rule to CEL-as-rule. Existing regex rules migrate mechanically to `txn.description.matches(...)`.

## Capabilities

### New Capabilities
- `household-ledger`: Double-entry books derived from classification. Accounts (assets/liabilities), nominals (the category tree), journal entries, posting shapes for spend / income / transfer / split.
- `cel-rule-language`: CEL as the stored, sandboxed, compile-once rule language inside the rule gatherer; typed activation; dry-run validation; mechanical regex migration.
- `cohort-discovery`: Iterative grouping of unclassified transactions; CEL synthesis (templates first, LLM second); residual covering; coverage reporting in groups.
- `autonomous-review`: ADHD operating model — interrupt budget, money-at-risk gate, cohort as the review unit, skip-is-safe, weekly ritual instead of a daily firehose.

### Modified Capabilities
- `transaction-classification`: Rule evidence may be produced by a CEL match, not only a description regex. Policy, tiers, itemized invariant, contested→review are unchanged.
- `evidence-model`: Rule evidence `source` identifies a CEL rule id; gatherers still do not decide.
- `rule-bootstrap`: Bootstrap produces CEL predicates over cohorts, not first-token regexes, and uses residual covering so mixed clusters get split instead of one sloppy pattern.
- `classification-learning`: The learner proposes CEL rules (not escaped merchant keys) and still requires ≥1 human confirmation.
- `review-and-learning`: Review is cohort-first; per-transaction review remains only for residuals that will not cluster.

## Impact

- **Affected code (later slices, not this docs change):** `classification/gatherers/rules.py`, `classification/db_sources.py`, `classification/bootstrap.py`, `classification/learning.py`, `classification/review.py`, `services/transaction_clustering_service.py`, `services/rule_validation_service.py`, `services/interactive_refinement_service.py`, `models/classification_rule.py`, new ledger models (`accounts`, `journal_entries`, `postings`), cockpit UI in `apps/web/` (still a skeleton).
- **Dependencies:** `celpy` (pure-Python CEL; chosen because gb10 is ARM64 and we should not take a C++/Rust native wheel). No new cloud services. Policy gate stays human-owned.
- **Data:** `classification_rules.rule_expression` becomes CEL. New ledger tables. Existing 4k+ ingested transactions remain source facts; they gain postings as they are classified / reprocessed.
- **Operations:** Nightly sync → classify → discover-cohorts → learn still runs unattended. Human touch is a weekly Quiet Ledger ritual when the interrupt budget is exceeded.
- **Out of scope:** budgeting dashboards, multi-user auth, Outlook/M365 mailbox, DSPy/GEPA, full offsetting-movement transfer matcher (CEL is per-transaction; pairing stays a gatherer), implementing the current one-transaction cockpit as specified.
- **Supersedes (design, not code):** the June 2026 decision "rules only need description matching, drop the DSL". CEL is not that DSL. It is a sandboxed expression language *inside* the gatherer, which is the altitude the earlier design correctly asked for.

## Open Questions

- Exact money-at-risk thresholds (absolute vs relative-to-merchant). Tune after the gate exists; start with a conservative household default (e.g. auto-apply below a configured minor-unit cap unless contested).
- Whether opening balances / historical backfill post into the ledger in one shot after bootstrap, or only going forward. Recommendation: reprocess after the first confirmed CEL cohort set, because the current decisions have no postings.
- Whether `celpy`'s RE2-style `matches()` is close enough to today's Python `re.search` for migrated rules. Spike in slice 1 with the live rule cache.
