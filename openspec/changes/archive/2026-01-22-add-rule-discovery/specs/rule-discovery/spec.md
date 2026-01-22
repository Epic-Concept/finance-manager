# Capability: Rule Discovery

This capability enables intelligent discovery and creation of classification rules from historical transaction data.

---

## ADDED Requirements

### Requirement: Transaction Clustering

The system SHALL group similar transactions into clusters for pattern analysis.

#### Scenario: Clustering by normalized description
Given a set of uncategorized transactions
When clustering is performed
Then transactions with similar normalized descriptions are grouped together
And each cluster contains transactions that could be covered by a single rule

#### Scenario: Description normalization
Given a transaction description "TESCO STORES 1234"
When the description is normalized
Then the result is "TESCO" (uppercase, store number removed, suffix stripped)
And this matches other transactions like "tesco express" and "TESCO EXTRA 5678"

#### Scenario: Cluster ranking
Given multiple clusters of varying sizes
When clusters are ranked
Then they are ordered by size (largest first)
And coverage percentage is calculated for each cluster

---

### Requirement: Rule Proposal Generation

The system SHALL generate classification rule proposals using LLM analysis of transaction clusters.

#### Scenario: LLM proposes rule for cluster
Given a cluster of 50 similar transactions
And the available category hierarchy
When a rule proposal is requested
Then the LLM returns a regex pattern that matches the cluster
And suggests an appropriate category from the hierarchy
And provides a confidence level (high/medium/low)
And includes reasoning for the suggestion

#### Scenario: Proposal persistence
Given a generated rule proposal
When the proposal is created
Then it is persisted to the rule_proposals table
And includes the cluster hash for deduplication
And has status "pending"

---

### Requirement: Rule Validation

The system SHALL validate proposed rules against all transactions to measure precision.

#### Scenario: Precision calculation
Given a proposed rule pattern
And the target cluster of transactions
When validation is performed
Then the rule is tested against ALL transactions
And true positives (matches in cluster) are counted
And false positives (matches outside cluster) are counted
And precision is calculated as TP / (TP + FP)

#### Scenario: False positive sampling
Given a proposed rule with false positives
When validation results are generated
Then a sample of false positive descriptions is included
And the user can review which unintended transactions would match

#### Scenario: Conflict detection
Given a proposed rule pattern
And existing classification rules
When conflict check is performed
Then overlapping rules are identified
And the user is warned about potential conflicts

---

### Requirement: Rule Proposal Tracking

The system SHALL track proposal status for audit trail and resumability.

#### Scenario: Proposal status transitions
Given a rule proposal with status "pending"
When the user accepts the proposal
Then a classification_rule is created with the pattern
And the proposal status changes to "accepted"
And the proposal links to the created rule via final_rule_id

#### Scenario: Rejection tracking
Given a rule proposal with status "pending"
When the user rejects the proposal
Then the proposal status changes to "rejected"
And reviewer_notes can be stored for reference
And the proposal is preserved for audit

#### Scenario: Resume from pending
Given rule proposals with status "pending" from a previous session
When the discovery CLI is started with --resume flag
Then pending proposals are loaded
And the user can continue reviewing where they left off

---

### Requirement: Interactive Discovery CLI

The system SHALL provide an interactive CLI for reviewing and approving rule proposals.

#### Scenario: Cluster display
Given uncategorized transactions have been clustered
When the CLI displays a cluster
Then it shows the cluster size and coverage percentage
And shows sample transaction descriptions
And shows the normalized pattern

#### Scenario: Accept rule
Given a displayed rule proposal
When the user presses 'A' to accept
Then the rule is saved to classification_rules table
And the proposal is marked as accepted
And the CLI moves to the next cluster

#### Scenario: Modify rule
Given a displayed rule proposal
When the user presses 'M' to modify
Then the user can edit the regex pattern
And the modified pattern is re-validated
And the modified rule can be accepted

#### Scenario: Analyze-only mode
Given the CLI is started with --analyze-only flag
When analysis runs
Then transactions are clustered and statistics displayed
But no LLM calls are made
And no rule proposals are generated

---

### Requirement: Batch Classification CLI

The system SHALL provide a CLI for running batch classification with current rules.

#### Scenario: Classify all uncategorized
Given classification rules exist
And uncategorized transactions exist
When classify_batch.py is run
Then all uncategorized transactions are evaluated against rules
And matching transactions are classified
And a summary of classifications is displayed

#### Scenario: Coverage statistics
Given the CLI is run with --stats-only flag
When statistics are generated
Then total transaction count is shown
And categorized count is shown
And uncategorized count is shown
And coverage percentage is calculated
And breakdown by classification method (rule/ai/manual) is shown

#### Scenario: Idempotent classification
Given a transaction is already classified
When batch classification runs
Then the transaction is skipped (not re-classified)
Unless --force flag is provided
