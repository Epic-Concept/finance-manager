## ADDED Requirements

### Requirement: Review queue surface

The system SHALL expose an API to list pending review items (transaction summary, proposed categorization, strength/reason, and the supporting evidence) and to resolve each by confirming, reclassifying, or marking it an internal transfer.

#### Scenario: Listing pending reviews

- **WHEN** the review list is requested
- **THEN** it returns the decisions routed to review with their proposed categorization and evidence

#### Scenario: Resolving a review item

- **WHEN** the operator confirms or corrects a review item's categorization
- **THEN** the transaction's categorization is applied and the item leaves the pending queue

### Requirement: Confirmation feeds the learner

A resolved review (and an un-corrected auto-apply) SHALL be emitted as a learner observation marked human-confirmed when the operator acted, so the shadow learner can promote stable rules.

#### Scenario: A confirmed correction becomes a human-confirmed observation

- **WHEN** the operator resolves a review item
- **THEN** a learning observation for that merchant→category is recorded with `human_confirmed = true`

### Requirement: Scheduled rule promotion

The system SHALL run the shadow learner on a schedule over accumulated observations and create rules for clusters that meet the stability criteria (consistent, sufficient, ≥1 human-confirmed), off the classification hot path.

#### Scenario: Stable confirmed pattern is promoted

- **WHEN** the scheduled learner runs and a merchant meets the stability criteria
- **THEN** a new rule is created so future transactions for that merchant are auto-applied by the rules fast-path

#### Scenario: Promotion never blocks classification

- **WHEN** the learner runs
- **THEN** it operates on persisted observations and does not run inside the classification request path
