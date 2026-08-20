# ADR-002: Autonomous Household Ledger

## Status
Proposed

## Context

Finance Manager is a local-first household app. Classification is already the core: gatherers emit typed evidence, a deterministic policy auto-applies or routes to review, and a shadow learner promotes rules only after human confirmation. That architecture is right.

The product around it is still a bookkeeping chore:

- There is no ledger. A bank row gets a category sticker (`transaction_categories`) or a decision with splits. There are no postings, no asset accounts, no way to say "this moved from Current to Savings" without overloading a category.
- Rules were originally boolean expressions (`description =~ "..."`, `amount < 0`, `account_name == "..."`). The evidence-driven rebuild collapsed them to a description regex because "rules only need description matching." Real household rules are not description-only: salary vs refund by sign and amount, rent by day-of-month, the same merchant string on two accounts, round-ups, internal names that must never be spend.
- Clustering is the first significant token after stripping numbers. That is a good first cut and a bad last cut. Mixed "TESCO" clusters and one-off transfers fall through as hundreds of review cards.
- The planned Quiet Ledger cockpit treats the human work unit as one transaction. For ADHD that is the wrong grain: initiation cost is paid per card, and a 200-item queue will be avoided rather than cleared.
- The operator procrastinates finance. The system has to be largely autonomous and bother them as little as possible.

The operator asked to rethink the product around a ledger, the existing nominals, a transaction classifier as the holy grail, CEL-stored rules, and an iterative process that finds groups of transactions.

## Decision

1. **Keep gather/decide.** CEL, clustering, and the ledger do not replace the evidence policy. Rules remain a gatherer. Splits still require itemized `PROOF`. Contested still goes to review. The learner still cannot silently change the required-tier table.

2. **The classifier writes a ledger, not a label.** Immutable bank transactions are source facts. A classification decision produces a balanced journal entry: spend/income against a nominal, transfers between asset accounts, splits as N nominal postings plus one asset posting.

3. **Nominals are the existing category tree.** Commitment levels (Survival → Future) and Internal Transfer stay. Asset/liability accounts are a new, small chart (current, savings, cards, cash). We do not expose accounting jargon in the UI.

4. **Rules are CEL expressions over a typed activation**, stored in `rule_expression`, compiled once, evaluated many times, sandboxed, side-effect free. Library: `celpy` (pure Python, ARM64-friendly on gb10). Amounts enter CEL as integer minor units, never floats.

5. **The human work unit is a cohort.** Sequential covering: cluster unclassified rows, synthesize a CEL predicate (templates first, LLM only when templates fail), dry-run for false positives, specialize or split, confirm once, remove the covered residual, repeat.

6. **ADHD operating model.** Default interrupt budget is zero per day. Remaining uncertainty is a weekly, skippable ritual. Immediate interrupt only for money-at-risk, contested, or novel large unknowns. Skip never punishes; the system keeps classifying what it can.

7. **Do not ship the one-transaction cockpit as specified.** Reuse Quiet Ledger visual language; change the card to a cohort.

## Consequences

### Positive
- One confirmed cohort can mint a rule and post dozens of entries.
- Rules can express amount, account, sign, and date without a custom DSL or arbitrary Python.
- The books become correct enough to answer "what did we actually spend" without a spreadsheet.
- Review load falls as coverage grows; missed weeks do not create a shame pile if the unit is groups.

### Negative
- CEL `matches()` is RE2-ish, not Python `re`. Migrated regexes need a compatibility spike.
- Cross-transaction transfer pairing cannot live in CEL (no joins). It stays a gatherer, still deferred as a full subsystem.
- Reprocessing historical decisions is required before the ledger is trustworthy.
- The open `add-classification-cockpit` change must be revised before implementation.

### Neutral
- Evidence tiers, mailbox receipt hunts, and the local LLM stay as they are.
- Nightly sync from Azure SQL stays the ingestion path.
