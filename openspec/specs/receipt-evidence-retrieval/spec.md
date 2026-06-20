# receipt-evidence-retrieval Specification

## Purpose

Defines the agentic receipt-hunting workflow: searching across household mailboxes within time windows, candidate ranking, line-item extraction via the local LLM, total reconciliation banding, and honest ambiguity reporting.

## Requirements

### Requirement: Multi-mailbox receipt search

The system SHALL search across all configured household mailboxes for a receipt matching a transaction, using the merchant, amount, and a configurable date window around the transaction date. Searching multiple mailboxes SHALL be supported because the paying person is not always known in advance.

#### Scenario: Receipt found in one mailbox

- **WHEN** exactly one mailbox contains a strongly matching receipt within the date window
- **THEN** the gatherer returns receipt evidence sourced from that mailbox

#### Scenario: No receipt within the initial window

- **WHEN** no matching receipt is found in any mailbox within the default date window
- **THEN** the gatherer widens the window once per its configuration and, if still none, returns no-receipt evidence

### Requirement: Local-LLM line-item extraction

The system SHALL extract receipt line items (description, amount, quantity) using the local LLM on `gb10.local`, and SHALL NOT send raw mailbox content to a cloud provider.

#### Scenario: Raw email stays on-prem

- **WHEN** a candidate receipt email is parsed for line items
- **THEN** extraction is performed by the local on-prem model and the raw email content is not transmitted to a cloud LLM

### Requirement: Total reconciliation banding

The system SHALL compare the sum of extracted line items against the transaction total and SHALL set receipt evidence strength by reconciliation band: within tolerance yields itemized `PROOF`; a moderate mismatch yields a flagged `STRONG`; a large mismatch yields `WEAK` and SHALL NOT be trusted as a split.

#### Scenario: Reconciling receipt is PROOF

- **WHEN** the line-item sum matches the transaction total within tolerance
- **THEN** the receipt evidence is itemized at the `PROOF` tier

#### Scenario: Large mismatch is untrusted

- **WHEN** the line-item sum differs from the transaction total beyond the large-mismatch band
- **THEN** the receipt evidence is assigned `WEAK` and is not used to auto-apply a split

### Requirement: Honest ambiguity reporting

When receipt retrieval is ambiguous, the system SHALL degrade evidence strength and report the ambiguity rather than guessing. Ambiguity (such as a plausible receipt found in more than one mailbox) is itself an evidence fact the policy MAY act on.

#### Scenario: Matching receipts in two mailboxes

- **WHEN** plausible matching receipts are found in two different household mailboxes
- **THEN** the gatherer reports the ambiguity and returns degraded-strength evidence rather than selecting one arbitrarily
