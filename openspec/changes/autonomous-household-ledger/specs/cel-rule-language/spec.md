# cel-rule-language Specification

## Purpose

Defines Common Expression Language (CEL) as the stored rule language evaluated by the rule gatherer. Expressions are sandboxed, side-effect free, compiled once, and emit `Evidence` only. They do not replace the deterministic evidence policy.

## ADDED Requirements

### Requirement: Rules are CEL booleans

An active classification rule's `rule_expression` SHALL be a CEL expression that evaluates to true or false against a typed transaction activation. A true result SHALL cause the rule gatherer to emit non-itemized `RULE` evidence for that rule's category. A false result SHALL emit nothing. Gatherers SHALL NOT write a final categorization.

#### Scenario: Matching rule emits evidence

- **WHEN** the highest-priority active rule evaluates to true for a transaction
- **THEN** the gatherer emits `Evidence` with type `RULE`, the rule's category as claim, `itemized=false`, and a source identifying that rule

#### Scenario: Non-matching rules emit nothing

- **WHEN** no active rule evaluates to true
- **THEN** the rule gatherer returns an empty evidence list

### Requirement: Typed activation without floating money

The activation SHALL expose at least `txn.description`, `txn.merchant`, `txn.account`, `txn.currency`, `txn.amount_minor` (integer, sign preserved, amount × 10^4), `txn.day_of_month`, and `txn.is_debit`. Monetary comparisons in rules SHALL use `amount_minor` or equality on that integer, never a floating-point amount.

#### Scenario: Amount-constrained subscription

- **WHEN** a rule is `txn.amount_minor == 125000 && txn.description.matches("(?i)netflix")`
- **THEN** only transactions whose scaled amount is exactly 125000 and whose description matches are evidence-positive

### Requirement: Invalid expressions are skipped

An expression that fails to compile or throws at evaluation SHALL be skipped and SHALL NOT fail the classification run. The skip SHALL be logged.

#### Scenario: Broken rule does not abort classify

- **WHEN** one active rule is not valid CEL and a later rule is valid and matches
- **THEN** the invalid rule is skipped and the later rule may still emit evidence

### Requirement: First match wins

Active rules SHALL be evaluated in priority order (then id). The first true result wins; later rules are not evaluated for that transaction.

#### Scenario: Specific rule beats catch-all

- **WHEN** a high-priority merchant rule and a later catch-all would both match
- **THEN** only the high-priority rule emits evidence

### Requirement: Mechanical migration of regex rules

Existing `rule_expression` values that are description regexes or `description =~ "..."` forms SHALL be migrated to CEL `txn.description.matches("...")` without changing their category or priority. After migration, dry-run coverage of migrated rules against stored transactions SHALL match the pre-migration regex gatherer except where the documented CEL dialect differs, in which case the difference SHALL be listed and fixed or wrapped.

#### Scenario: Learner-escaped merchant key still matches

- **WHEN** a rule stored as a Python-escaped merchant token is migrated
- **THEN** transactions that matched the regex gatherer still produce RULE evidence

### Requirement: Dry-run validation

The system SHALL evaluate a candidate CEL expression against stored transactions and report true positives, also-matches (unlabelled), false positives (labelled as a different nominal), and conflicts with other active rules.

#### Scenario: False positive against a confirmed label

- **WHEN** a candidate matches a transaction already confirmed to a different category
- **THEN** the dry-run reports that row as a false positive
