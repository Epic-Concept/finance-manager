## ADDED Requirements

### Requirement: Uniform Evidence type

The system SHALL represent every piece of information used in a classification decision as a typed `Evidence` object carrying: the `claim` it supports (a single category, or an itemized split), the `type` (e.g. `RULE`, `HISTORY`, `WEB_LOOKUP`, `RECEIPT`, `LLM_INFERENCE`), the `source` (an identifier such as a rule id, prior-transaction set, URL, email id, or model name), a `strength` tier, and an `itemized` flag indicating whether it justifies a split or only a single category.

#### Scenario: Rule gatherer emits non-itemized evidence

- **WHEN** a fixed rule matches a transaction description
- **THEN** the gatherer emits an `Evidence` object with `type=RULE`, the matched category as its claim, `itemized=false`, and a `source` referencing the rule

#### Scenario: Receipt gatherer emits itemized evidence

- **WHEN** a receipt is retrieved and parsed into line items for a transaction
- **THEN** the gatherer emits an `Evidence` object whose claim is a split across categories, `type=RECEIPT`, and `itemized=true`

### Requirement: Strength tier ordering

The system SHALL classify evidence strength into the discrete ordered tiers `PROOF > STRONG > WEAK > NONE`, and SHALL NOT represent strength as a single continuous score used with a numeric threshold. Tier assignment SHALL be derived from provenance, match quality, and completeness rather than from corroboration count alone.

#### Scenario: Tiers are comparable

- **WHEN** the policy compares two pieces of evidence supporting different claims
- **THEN** the evidence at the higher tier is treated as stronger, independent of how many lower-tier pieces support the alternative claim

#### Scenario: Bare LLM guess is WEAK

- **WHEN** the only evidence for a claim is an LLM inference from the transaction description with no corroborating receipt or history
- **THEN** that evidence is assigned the `WEAK` tier

### Requirement: Gatherers do not decide

A gatherer SHALL only produce `Evidence` and SHALL NOT assign a final category or split to a transaction. The mapping from collected evidence to a final categorization SHALL be performed exclusively by the evidence policy.

#### Scenario: Gatherer returns evidence, not a decision

- **WHEN** any gatherer (rule, history, web lookup, receipt, LLM) runs against a transaction
- **THEN** its output is a set of `Evidence` objects and it performs no write of a final category to the transaction

### Requirement: Pluggable gatherer contract

The system SHALL expose a single interface that all gatherers implement, so that gatherers can be added or removed without changing the policy. Each gatherer SHALL declare the evidence types it can produce and SHALL report honest strength, including degraded strength when its result is ambiguous or low-confidence.

#### Scenario: Adding a gatherer requires no policy change

- **WHEN** a new gatherer implementing the contract is registered
- **THEN** the policy consumes its evidence using the existing tier and combination rules without modification
