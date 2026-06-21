# rule-bootstrap Specification

## Purpose

Cold-start bootstrapping of the rule cache from unlabelled data — cluster → LLM-propose-per-cluster → human-confirm → seed rules; plus seeding categories and handling intra-family/business transfers.

## Requirements

### Requirement: Interactive cluster bootstrap

The system SHALL provide a runnable bootstrap that clusters the stored transactions, presents the largest clusters first with the LLM's proposed category, and lets the operator confirm or correct each before any rule is created. No rule SHALL be created without operator confirmation.

#### Scenario: Operator confirms a proposed cluster category

- **WHEN** the operator confirms (or corrects) a cluster's proposed category
- **THEN** a rule mapping that cluster's pattern to the confirmed category is created and is active

#### Scenario: Skipped cluster creates no rule

- **WHEN** the operator skips a cluster
- **THEN** no rule is created for it

### Requirement: Category and transfer seeding

The system SHALL seed the category hierarchy on gb10 and SHALL include an internal-transfer category so intra-family/business movements (which are not spend) can be assigned during bootstrap rather than mis-categorized as purchases.

#### Scenario: Categories are present before bootstrap

- **WHEN** the bootstrap runs
- **THEN** the category hierarchy (including an internal-transfer category) exists for proposals and rules to reference

#### Scenario: A self-transfer cluster is assignable to transfer

- **WHEN** the operator labels a cluster of intra-family/business transfers
- **THEN** it can be assigned the internal-transfer category and is not treated as spend

### Requirement: Coverage reporting

The bootstrap SHALL report cluster coverage (how many transactions the confirmed clusters account for) so the operator can see the labelling effort vs. coverage tradeoff.

#### Scenario: Coverage is reported

- **WHEN** the bootstrap presents clusters
- **THEN** it reports the share of transactions covered by the top clusters
