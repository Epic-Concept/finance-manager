# cohort-discovery Specification

## Purpose

Defines iterative grouping of unclassified transactions: hierarchical clustering, CEL synthesis (templates first, LLM second), dry-run specialization, residual covering, and human confirmation of a cohort as the way rules are born.

## ADDED Requirements

### Requirement: Sequential covering over residuals

The system SHALL discover candidate cohorts from transactions that are not yet posted, largest stable group first. After a cohort is confirmed, matching residual transactions SHALL be removed from the working set and discovery SHALL continue on what remains.

#### Scenario: Confirming a grocery cohort leaves leftovers

- **WHEN** the operator confirms a Tesco→Groceries CEL rule
- **THEN** matching Tesco rows leave the residual and the next proposed cohort is computed from the rest

### Requirement: Hierarchical cluster keys

Discovery SHALL cluster by more than the first description token. It SHALL at least attempt fixed `(merchant, amount, account)` groups, then `(merchant, sign, account)`, then merchant token, then `(amount, cadence)` groups, and treat remaining rows as residual.

#### Scenario: Subscriptions separate from variable tickets

- **WHEN** residual contains a £12.99 monthly Netflix and other Netflix-shaped one-offs
- **THEN** discovery may propose a fixed-amount cohort distinct from a variable-amount merchant cohort

### Requirement: Template synthesis before LLM

The system SHALL propose a CEL predicate from deterministic templates (escaped merchant, optional sign, optional account, optional exact amount, optional day-of-month) and SHALL invoke an LLM to emit CEL only when templates cannot reach acceptable precision against already-labelled rows. LLM output SHALL be compiled and dry-run; failure SHALL discard the predicate.

#### Scenario: Clean merchant cluster needs no LLM

- **WHEN** a unanimous debit cluster keyed by merchant has no labelled false positives under the template predicate
- **THEN** the proposed CEL is the template and no LLM call is required for the predicate

#### Scenario: Invalid LLM CEL is discarded

- **WHEN** the model emits an expression that does not compile
- **THEN** that expression is not shown as a confirmable cohort predicate

### Requirement: Mixed clusters split rather than overfit

If a cluster cannot be covered by one high-precision predicate, the system SHALL split it (or present it as multiple cohorts) rather than proposing a catch-all that false-positives against labelled rows.

#### Scenario: Polluted first-token cluster

- **WHEN** the merchant token groups two different intents with different confirmed nominals
- **THEN** discovery does not propose a single rule for the whole token

### Requirement: One confirmation mints a rule and covers the group

Confirming a cohort SHALL create an active CEL rule and SHALL classify the residual transactions matched by that rule (subject to the evidence policy). Skip SHALL create no rule. Changing the nominal SHALL store the rule against the chosen category.

#### Scenario: Confirm covers the samples

- **WHEN** the operator confirms a cohort of size N whose predicate matches those N residual rows
- **THEN** an active rule is stored and those N rows are no longer residual

### Requirement: Coverage is reported in groups

Discovery SHALL report how many residual transactions the confirmed cohorts cover, and the size of the remaining residual, so effort-vs-coverage is visible without listing every row.

#### Scenario: Coverage bar after two confirms

- **WHEN** two cohorts totalling 40% of residual have been confirmed
- **THEN** the reported coverage reflects that 40% and the leftover count
