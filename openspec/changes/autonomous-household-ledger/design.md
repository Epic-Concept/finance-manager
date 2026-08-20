# Autonomous Household Ledger — Design

## Context

The live system on `gb10.local` already does the hard architectural thing: **messy gatherers, deterministic policy**. Nightly Azure SQL pull, Postgres, local LLM, mailbox receipt hunts, a shadow learner, ~4k ingested transactions, and a seeded ~117-category tree with commitment levels plus Internal Transfer. The planned Quiet Ledger cockpit is still a Vite skeleton.

What failed for the human is not intelligence. It is **grain and books**:

| Today | Problem |
|---|---|
| Category sticker on a bank row | Cannot represent transfers, splits, or "which pocket of money" without overloading categories |
| `RuleGatherer` is `re.search(pattern, description)` | Cannot constrain amount, account, sign, day-of-month; `rule_expression` used to be a boolean DSL and was flattened to a regex |
| Cluster key = first token | "TESCO" and "PRZELEW" lumps mixed intents; leftovers become per-row review |
| Review = one decision card | ADHD poison: initiation cost × N, a queue that grows while avoided |
| Learner emits `re.escape(merchant_key)` | Promotes the same first-token bluntness that clustering used |

The June 2026 design was right to kill the custom `rule-engine` DSL and to forbid gatherers from deciding. It was wrong to conclude that description matching is the whole rule. The operator's prompt restores the missing pieces without undoing gather/decide: **ledger + nominals, CEL rules, iterative groups, bother me as little as possible.**

## Goals / Non-Goals

**Goals**
- A household ledger whose journal is produced by the classifier.
- CEL as the stored rule language inside the rule gatherer.
- Iterative cohort discovery so one human action covers many transactions and yields a durable rule.
- An ADHD operating model: autonomy first, grouped exceptions, skip-is-safe, interrupt budget.
- Preserve evidence policy, privacy (nothing new leaves gb10), exact decimal money, ≥1 human confirmation before rule promotion.

**Non-Goals**
- Replacing the evidence policy with an agent that "just decides".
- Full GAAP, tax packing, or multi-entity accounting.
- Budgeting / analytics dashboards (they become cheap once postings exist; not this change's UI).
- Implementing the current one-transaction cockpit as specified.
- Cross-transaction transfer pairing as a complete subsystem (shape the ledger so it can land later).
- DSPy/GEPA, Outlook mailbox, multi-user auth.

## North star

**The system is the bookkeeper. The human is the auditor of exceptions.**

A good week is: sync ran, 40 new rows arrived, 37 posted by CEL/history, 3 sat in a cohort "new merchant cluster — looks like pharmacies", and nobody was pinged. A good human session is five minutes, one cohort, Enter. A bad session is 200 cards that look alike.

## Layering (do not flatten)

```
┌─────────────────────────────────────────────────────────────┐
│  Source facts (immutable)                                   │
│  Bank / card transactions from Azure SQL                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Classifier (holy grail)                                    │
│  Gatherers (CEL rules, history, web, receipt, LLM)          │
│       → Evidence → deterministic policy → Decision          │
│  Cohort discovery mints CEL rules off the hot path          │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Ledger (derived, re-postable)                              │
│  Balanced journal entry per applied decision                │
│  Assets/liabilities = household pockets                     │
│  Nominals = existing category tree                          │
└─────────────────────────────────────────────────────────────┘
```

Classification is the mapping. The ledger is the effect. Source facts are never rewritten. Reclassify = reverse posting + new posting (append-only), pointing at the new decision. This is how Beancount/Ledger-style personal finance works, without exposing that jargon.

## Decision: Household ledger from classification

### Chart

Two kinds of account, only one of which is new:

1. **Pockets (asset / liability)** — Current, Savings, credit cards, cash. Small, stable, mapped from `transactions.account_name` (already ingested).
2. **Nominals (income / expense / internal)** — the existing `categories` tree, including commitment_level 0–4 and Internal Transfer. Not rewritten.

Equity/opening-balance is a single nominal used once per pocket when we backfill.

### Posting shapes

Every applied decision writes one journal entry whose postings sum to zero in minor units.

| Kind | Postings |
|---|---|
| Spend (N=1) | Dr nominal, Cr pocket |
| Income | Dr pocket, Cr income nominal |
| Split | Dr each nominal (receipt lines), Cr pocket (total) |
| Transfer | Dr destination pocket, Cr source pocket (no P&L) |
| Card payment | Dr card liability, Cr current (also a transfer shape) |

Sign of the source transaction chooses spend vs income when the claim is a P&L nominal. Internal Transfer and explicit transfer claims use the transfer shape even if the bank row looks like a spend.

### Why this is not optional

Without postings, " Groceries" on a card payment and "Groceries" on a current-account Tesco are the same label and a transfer to savings is fake spend. The classifier cannot be the holy grail if its output cannot become books.

### What we do not build yet

Trial balance UI, net-worth charts, budget envelopes. The schema must make those a query, not a rewrite.

## Decision: CEL inside the gatherer, not as the policy

### Why CEL, and why now

`classification_rules.rule_expression` was documented as a rule-engine expression. Tests still show the intended altitude:

- `description =~ "(?i)amazon.co.uk"`
- `account_name == "Joint Account" and description =~ "(?i)mortgage"`
- `amount < 0`

The gatherer then started treating the column as a raw regex. CEL is the portable, sandboxed language that column was reaching for.

CEL is a good fit because it is:

- **Non-Turing-complete** — no loops, guaranteed termination (safe to eval on every new txn).
- **Side-effect free** — a gatherer must not write.
- **Compile once, eval many** — nightly classify is a tiny batch; bootstrap dry-run is the hot loop.
- **Readable enough to show on a cohort card** — the human is confirming a predicate, not a neural net.
- **LLM-writable with a schema** — much safer than "emit Python".

It is **not** a rewrite of the June decision to drop `rule-engine`. That library mixed matching with deciding. CEL only answers "does this fact match?", and the policy still maps evidence to auto-apply vs review.

### Library: `celpy`

gb10 is ARM64. Official `cel-expr-python` wraps C++; `common-expression-language` wraps Rust. Both are better CEL-spec citizens and worse operational citizens here. **`celpy` (Cloud Custodian's pure-Python implementation)** installs anywhere we already run Python 3.11.

Slice 1 includes a locked dialect test: the operators we actually emit must evaluate identically across fixtures. If `celpy` diverges on `matches()`, we constrain synthesis to the subset that works, not the whole spec.

### Typed activation

Amounts **never** enter CEL as floats. The activation is:

```
txn.description: string
txn.merchant:    string   # merchant_name or ""
txn.account:     string   # account_name or ""
txn.currency:    string
txn.amount_minor: int     # Numeric(19,4) × 10^4, sign preserved
txn.day_of_month: int
txn.weekday:     int      # 0=Mon … 6=Sun if useful; optional
txn.is_debit:    bool     # amount_minor < 0
```

Custom functions, if any, stay tiny (`norm(string)` for the existing merchant-token normalizer). Prefer CEL builtins: `contains`, `startsWith`, `matches`, `&&`, `||`, `!`, comparisons.

### Dialect we will actually synthesize

```
txn.description.matches("(?i)tesco")
txn.is_debit && txn.description.matches("(?i)tesco")
txn.account == "Santander Current" && txn.description.matches("(?i)mortgage")
txn.amount_minor == 125000 && txn.description.matches("(?i)netflix")
txn.day_of_month <= 5 && txn.description.matches("(?i)rent")
```

Priority remains "first matching active rule wins". Invalid CEL is skipped (same as invalid regex today), never fatal on the classify path.

### Migration of existing rules

If `rule_expression` already looks like CEL (`txn.` prefix or `&&`), leave it. If it looks like `description =~ "PAT"`, extract `PAT`. Otherwise treat the whole string as a Python regex and wrap:

```
txn.description.matches("PAT")
```

Learner-promoted `re.escape(merchant_key)` rules wrap the same way. Dry-run on the live store in slice 1; any precision drop vs the regex gatherer is a bug.

### What CEL must not do

- Join to other transactions (transfer pairing).
- Call the mailbox or the LLM.
- Write to the database.
- Encode policy tiers ("this is PROOF"). Strength stays a property of *being an approved rule*, not of the expression.

## Decision: Iterative cohort discovery (sequential covering)

This is the bootstrap **and** the ongoing learner's search procedure. The current "cluster by first token → LLM category → regex of that token" is step 0 of this, not the product.

### Algorithm

```
residual ← all transactions without an applied posting
rules    ← active CEL rules
repeat until residual is small or no stable cohort remains:
    1. Cluster residual (hierarchical features, largest first)
    2. For each cluster that meets min size:
         pred ← synthesize_cel(cluster)          # templates first
         report ← dry_run(pred, ALL transactions)
         while report.false_positives and not stuck:
             pred ← specialize(pred, report)     # AND a tighter clause, or split cluster
             report ← dry_run(...)
         if report.precision is acceptable:
             propose Cohort(samples, pred, category, report)
    3. On confirm: persist CEL rule, apply to residual matches, post ledger entries
    4. residual ← residual minus newly covered
```

"Precision is acceptable" for auto-proposal is **no false positives against already-labelled rows**. Unlabelled matches outside the cluster are not automatically FPs — they are *coverage* and must be shown as "also matches". The human is the one who says those extras are OK.

### Clustering features (cheap → specific)

Not just `words[0]`.

| Stage | Key | What it catches |
|---|---|---|
| A | `(norm_merchant, amount_minor, account)` | Subscriptions, rent, salary |
| B | `(norm_merchant, sign, account)` | Same shop, variable ticket |
| C | `norm_merchant` (today's first token) | Bulk grocery / transit |
| D | `(amount_minor, cadence)` | "£500 on the 1st" with messy descriptions |
| E | Residual outliers | Receipt/LLM path, or a singleton review |

`TransactionClusteringService` stays as stage C. New code layers A/B/D on top and feeds E to expensive gatherers instead of to a regex.

### Synthesis: templates first, LLM second

Deterministic templates, in order, until dry-run precision against labelled rows is 1.0:

1. `txn.description.matches("(?i)" + re.escape(cluster_key))`
2. AND `txn.is_debit` / `!txn.is_debit` if the cluster is unanimous on sign
3. AND `txn.account == "..."` if the cluster is unanimous **and** the unconstrained predicate collides on another account
4. AND `txn.amount_minor == N` if stage A (fixed amount)
5. AND `txn.day_of_month` range if stage D

LLM synthesis (local model, structured CEL-only output) runs only when templates cannot separate FPs. The model may not invent functions. Every LLM predicate is compiled and dry-run; compile failure discards it.

This replaces most of `InteractiveRefinementService`'s chat loop. Conversation is an escape hatch for polluted clusters, not the default ADHD path.

### Dry-run is the source of truth

Generalize `RuleValidationService` to evaluate CEL against the store:

- true positives: matches inside the cohort
- also-matches: unlabelled outside the cohort (show samples)
- false positives: matches that already have a *different* confirmed nominal
- coverage: TP / cohort size
- conflicts: other active rules that match the same ids (priority still decides; surface it)

A cohort card shows these numbers. Confirming a rule with FPs is possible but must be explicit (the Quiet Ledger equivalent of "I know").

## Decision: ADHD / autonomous review policy

The evidence policy stays the risk dial for *a single transaction*. This is the risk dial for *the human's attention*.

### Interrupt budget

| Channel | When |
|---|---|
| Silent | CEL or STRONG history auto-applies and amount is under the money-at-risk cap |
| Queue only | Needs a human, but not urgent — wait for the weekly ritual |
| Nudge | Weekly, if queue depth > 0: "3 cohorts, ~5 minutes" |
| Interrupt now | Contested, or unknown + `abs(amount_minor)` ≥ cap, or splittable merchant without itemized PROOF above the cap |

Default cap is configurable. Exact number is an open question; the *gate* is not. A large weekly Tesco should not trip the same wire as a large unknown merchant (relative-to-merchant exception, same as the deferred money-at-risk note in the 2026-06-20 design — it is deferred no longer as a *feature*, only as a *tuned constant*).

### Work unit

The review surface's primary card is a **cohort**:

- N transactions, date range, amount total
- 3–5 sample descriptions
- proposed nominal
- proposed CEL (monospace)
- precision / also-matches / FP samples
- actions: Confirm / Change nominal / Edit predicate / Split cluster / Skip

Per-transaction cards exist only for residuals that will not cluster (`min_cluster_size`). The unimplemented cockpit's one-card ritual is reused; the payload changes.

### Skip is safe

Skip means "not this week". The cohort remains, classify continues for everything else, no guilt metric, no streak. ADHD products fail when skipped work becomes a shame pile; grouping plus skip-without-penalty is the mitigation.

### Cold start

Bootstrap is the same algorithm with a larger residual (everything). Coverage bar stays — it is the one progress signal worth showing. "Confirm all high-confidence" remains human-triggered, never a silent bulk apply.

Do **not** run a first full classify that dumps thousands of review rows before cohort bootstrap. Operationalize-classification already warned about this; this design makes it a requirement.

## Decision: Quiet Ledger UI is redirected, not discarded

Keep: verdigris/paper tokens, Newsreader + Hanken Grotesk + Plex Mono, focus card, `c/e/s` keys, no gamification, Tailscale single-operator.

Change: bootstrap and daily review are the same cohort card. Overview shows coverage, auto-apply rate, **cohort** queue depth, and a rules table of CEL predicates. Do not implement `add-classification-cockpit` tasks 3–4 as a transaction firehose.

## What we keep from the current engine

- Evidence types, strength tiers, max-not-sum, contested → review
- Itemized invariant for splits
- Cheap-before-expensive collection loop
- Shadow learner off the hot path, ≥1 human confirmation
- Splits not cached unless exact recurring charge
- Local LLM + mailbox privacy boundary
- Nightly pull-sync, idempotent classify
- Category commitment levels

## Risks / Trade-offs

- **CEL `matches()` vs Python `re`** — migration spike; wrap and compare on live rules. Mitigation: dialect tests; fall back to a `python_re` custom function only if needed (prefer not to).
- **celpy spec drift** — lock a tiny dialect, not "all of CEL".
- **Template underfit** — first-token CEL will still over-match. Mitigation: dry-run against labelled FPs is mandatory before proposal.
- **LLM-emitted CEL** — could be nonsense or overly broad. Mitigation: compile + dry-run; never promote without the human (or the high-confidence hatch they pressed).
- **Ledger backfill** — old auto-applies have no postings. Mitigation: slice 3 reprocess from decisions after CEL migration; do not mix sticker-table reads with posting reads in the UI.
- **Attention budget vs missed fraud** — Mitigation: interrupt-now for large unknown; small misses wait a week by design (the operator already misses months).
- **Transfer pairing** — CEL cannot see the other leg. Mitigation: Internal Transfer nominal + later gatherer; do not fake pairing in CEL.

## Migration Plan (slices, not calendar)

See `tasks.md`. Rollback per slice: CEL evaluator can shadow-compare to regex before cutover; ledger tables are additive; cockpit is additive.

## Open Questions

- Money-at-risk cap and relative-to-merchant exception — pick a conservative default, measure queue, tune.
- Historical reprocess vs forward-only postings — recommend full reprocess after first confirmed CEL set.
- `celpy` `matches()` flags vs `(?i)` — spike in slice 1.
- Whether pockets are created automatically from distinct `account_name` values (yes, unless a name is garbage).
