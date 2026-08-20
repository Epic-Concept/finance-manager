# household-ledger Specification

## Purpose

Defines the household books: asset/liability pockets, the existing category tree as nominals, and balanced journal entries produced from applied classification decisions. Bank transactions remain immutable source facts.

## ADDED Requirements

### Requirement: Source facts stay immutable

The system SHALL treat ingested bank/card transactions as append-only source facts. Classification and reclassification SHALL NOT rewrite transaction amount, date, description, or external identity.

#### Scenario: Reclassification does not edit the bank row

- **WHEN** an applied categorization is corrected
- **THEN** the source transaction fields are unchanged and a new journal entry is written

### Requirement: Pockets and nominals

The system SHALL maintain a small chart of asset and liability pockets (household accounts) distinct from the category tree. Categories SHALL be the income, expense, and internal-transfer **nominals**. Each ingested `account_name` SHALL map to a pocket.

#### Scenario: A current-account spend posts to a pocket and a nominal

- **WHEN** a debit on account "Santander Current" is classified to Groceries
- **THEN** the journal credits the Santander Current pocket and debits the Groceries nominal

#### Scenario: Internal transfer is not spend

- **WHEN** a decision's claim is an Internal Transfer nominal
- **THEN** the journal moves value between pockets and does not post to an expense nominal

### Requirement: Balanced journal from a decision

Every auto-applied or human-confirmed classification decision SHALL produce one journal entry whose postings sum to zero in integer minor units (the transaction amount scaled by 10^4). Split claims SHALL produce one posting per split plus the balancing pocket posting.

#### Scenario: Single-category spend

- **WHEN** a decision auto-applies one expense category for the full amount
- **THEN** the entry has exactly two postings that sum to zero

#### Scenario: Itemized split

- **WHEN** a decision applies an itemized split that sums to the transaction total
- **THEN** the entry has one posting per split plus one balancing pocket posting, and the postings sum to zero

### Requirement: Reclassification is reversing

Correcting a decision SHALL reverse the previous entry (offsetting postings) and write a new balanced entry for the new claim. Prior postings SHALL remain in the audit trail.

#### Scenario: Category correction

- **WHEN** the operator reclassifies a posted transaction
- **THEN** the original postings are reversed and a new balanced entry is stored

### Requirement: Reports read postings, not stickers

New read models for spend, income, and transfers SHALL be derived from journal postings. The legacy `transaction_categories` sticker SHALL NOT be the source of truth for new surfaces.

#### Scenario: Transfer does not inflate spend

- **WHEN** spend for a period is queried
- **THEN** pocket-to-pocket transfer postings are excluded from expense totals
