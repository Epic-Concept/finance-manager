## ADDED Requirements

### Requirement: Cluster proposal review

The bootstrap surface SHALL present the largest transaction clusters, each with sample descriptions, the LLM's proposed category, and its confidence, ordered largest-first, and SHALL let the operator confirm, change the category, or skip each cluster.

#### Scenario: Reviewing a proposed cluster

- **WHEN** the bootstrap surface loads with generated proposals
- **THEN** it shows each cluster's samples, proposed category, and confidence, largest cluster first

#### Scenario: Confirming a cluster creates a rule

- **WHEN** the operator confirms a cluster (with the proposed or a changed category)
- **THEN** an active rule mapping that cluster to the chosen category is created

#### Scenario: Skipping a cluster creates nothing

- **WHEN** the operator skips a cluster
- **THEN** no rule is created for it and it leaves the working set

### Requirement: Live coverage feedback

The surface SHALL show how much of total transaction volume the confirmed clusters account for, updating as the operator confirms, so the labelling-effort-vs-coverage tradeoff is visible.

#### Scenario: Coverage updates on confirmation

- **WHEN** the operator confirms a cluster
- **THEN** the displayed coverage reflects the newly-covered transactions

### Requirement: Proposal generation is non-blocking

The surface SHALL NOT block on LLM proposal generation; it SHALL show generation progress when proposals are being (re)generated and operate on the cached proposal set.

#### Scenario: Proposals are still generating

- **WHEN** proposal generation is in progress
- **THEN** the surface shows progress rather than freezing, and shows proposals as they become available
