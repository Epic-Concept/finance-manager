## ADDED Requirements

### Requirement: At-a-glance classification health

The overview surface SHALL show current coverage (share of transactions with a decision), the auto-apply rate (share auto-applied vs. routed to review), and the pending-review count, as quiet live signal.

#### Scenario: Viewing system health

- **WHEN** the operator opens the overview
- **THEN** it shows coverage, auto-apply rate, and pending-review count from the current data

### Requirement: Browse rules

The overview SHALL let the operator browse the active rules (pattern, target category, and provenance such as bootstrap vs. learner-promoted) in a readable ledger table.

#### Scenario: Listing active rules

- **WHEN** the operator views the rules
- **THEN** each active rule is listed with its pattern and target category

### Requirement: Recently classified transactions

The overview SHALL show recently-classified transactions with their applied category, amount, and outcome (auto-applied vs. reviewed), so the operator can spot-check the system's behavior.

#### Scenario: Spot-checking recent classifications

- **WHEN** the operator views recent activity
- **THEN** recently-classified transactions are listed with category, amount, and outcome
