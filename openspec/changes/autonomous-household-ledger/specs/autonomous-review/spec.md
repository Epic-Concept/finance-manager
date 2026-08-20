# autonomous-review Specification

## Purpose

Defines the ADHD operating model: the human is the auditor of exceptions. Interrupt budget, money-at-risk gate, cohort as the primary review unit, skip-is-safe, and the weekly ritual instead of a per-transaction firehose.

## ADDED Requirements

### Requirement: Interrupt budget

The system SHALL NOT notify the operator by default when transactions auto-apply. Cases that need a human SHALL wait in a queue for a scheduled ritual unless they trip the interrupt-now gate. The ritual MAY be skipped without penalty.

#### Scenario: Quiet auto-apply

- **WHEN** a CEL rule auto-applies a grocery spend under the money-at-risk cap
- **THEN** no notification is sent and the row does not enter the human queue

#### Scenario: Skip does not escalate

- **WHEN** the operator skips the weekly ritual
- **THEN** queued cohorts remain queued, classify continues, and no additional nag is created that day

### Requirement: Interrupt-now is money-at-risk or contested

The system SHALL interrupt promptly only when a decision is contested, or when an unknown / below-tier case has absolute amount at or above a configured cap, or when a splittable merchant lacks itemized PROOF and is at or above that cap. A large known recurring merchant SHALL NOT use the same tripwire as an unknown merchant.

#### Scenario: Small unknown waits

- **WHEN** an unseen coffee-shop debit is below the cap and evidence is weak
- **THEN** it is queued for the ritual and does not interrupt

#### Scenario: Large unknown interrupts

- **WHEN** an unseen merchant debit is at or above the cap
- **THEN** it is marked interrupt-now rather than waiting silently for the weekly ritual

### Requirement: Cohort is the primary review unit

The human review surface SHALL present clustered cohorts (samples, proposed nominal, proposed CEL, dry-run counts) as the default queue item. Per-transaction review SHALL be used only for residuals that do not meet minimum cluster size.

#### Scenario: Many similar rows are one card

- **WHEN** 47 unclassified Tesco debits share a proposed Groceries CEL rule with no labelled false positives
- **THEN** the queue contains one cohort item, not 47 transaction items

#### Scenario: Singleton residual is a transaction card

- **WHEN** a leftover transaction belongs to no cohort of minimum size
- **THEN** it appears as an individual review item

### Requirement: Cold start does not dump a firehose

The system SHALL NOT run a first full classify that enqueues one review item per unclassified transaction before cohort discovery has been offered. Bootstrap and daily review SHALL share the cohort card.

#### Scenario: First run offers groups

- **WHEN** thousands of unlabelled rows exist and no CEL rules are confirmed yet
- **THEN** the operator is shown largest cohorts to confirm, not thousands of single-row cards

### Requirement: Confirm, change, skip on a cohort

The operator SHALL be able to confirm a cohort (mint rule + apply), change its nominal, request a split, or skip it. Keyboard confirm/change/skip MAY exist; pointer equivalents SHALL exist.

#### Scenario: Change nominal then confirm

- **WHEN** the operator changes a proposed category and confirms
- **THEN** the stored rule uses the chosen category
