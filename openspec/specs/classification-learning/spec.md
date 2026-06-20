# classification-learning Specification

## Purpose

Defines the async shadow learner: observing confirmed outcomes, proposing/promoting deterministic rules, the asymmetry between cacheable merchant-to-category mappings and non-cacheable splits, and the boundary that learning optimizes gatherers but never the human-owned policy gate.

## Requirements

### Requirement: Asynchronous shadow learning

The system SHALL observe confirmed `(evidence → decision)` outcomes asynchronously, outside the classification hot path. The shadow learner SHALL NOT block or alter live classification.

#### Scenario: Learning runs off the hot path

- **WHEN** a transaction is classified and its outcome confirmed
- **THEN** the outcome is emitted to the learner as an event and the classification response is not delayed by learning work

### Requirement: Stable rule promotion

The shadow learner SHALL propose new deterministic rules only from repeated, consistent, confirmed outcomes, and SHALL promote a proposed rule to active use only when its stability criteria are met. Promotion criteria SHALL include at least one human-confirmed outcome so that the system does not promote rules solely from its own prior auto-applied guesses.

#### Scenario: Consistent confirmed outcomes propose a rule

- **WHEN** a merchant maps to the same category across repeated confirmed outcomes meeting the stability criteria
- **THEN** the learner proposes a deterministic merchant-to-category rule

#### Scenario: Self-confirmation alone does not promote

- **WHEN** the only supporting outcomes for a candidate rule are the system's own prior auto-applies with no human confirmation
- **THEN** the learner does not promote the rule

### Requirement: Cache asymmetry between single-category and splits

The learner SHALL cache merchant-to-single-category mappings as reusable rules, and SHALL NOT cache multi-item split results as reusable rules, except when it detects a genuinely recurring identical charge (e.g. a fixed subscription bundle) matched by exact criteria.

#### Scenario: Single-category mapping is cached

- **WHEN** a merchant consistently resolves to one category
- **THEN** the learner may promote a reusable rule for that merchant

#### Scenario: Variable split is not cached

- **WHEN** a merchant's transactions split differently across orders
- **THEN** the learner does not promote a split template for that merchant

#### Scenario: Recurring identical charge may cache a template

- **WHEN** an identical recurring charge is detected by exact-match criteria
- **THEN** the learner may promote a split template scoped to that recurring charge

### Requirement: Learning boundary excludes the policy gate

The learner MAY optimize gatherers and their prompts against confirmed outcomes, but SHALL NOT silently modify the required-tier decision table or any other part of the deterministic policy gate. Any recalibration of the policy gate SHALL be measured, surfaced, and applied only with human approval.

#### Scenario: Gatherer optimization is allowed

- **WHEN** the learner improves a gatherer's mailbox query or extraction prompt based on confirmed outcomes
- **THEN** the change applies to the gatherer without altering the policy gate

#### Scenario: Policy recalibration requires a human

- **WHEN** measured accuracy suggests the required-tier table could be loosened or tightened
- **THEN** the system surfaces the recommendation for human approval and does not change the gate automatically
