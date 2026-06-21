## ADDED Requirements

### Requirement: Bootstrap proposal endpoints

The API SHALL expose endpoints to (a) trigger generation of cluster proposals (cluster the transactions and ask the LLM for a category per cluster) as a non-blocking job, (b) list the cached proposals with cluster samples, size, proposed category, confidence, and running coverage, and (c) apply a set of confirmations, creating an active rule per confirmed cluster and skipping the rest.

#### Scenario: Listing generated proposals

- **WHEN** the proposals list is requested and a cached set exists
- **THEN** it returns each cluster's samples, size, proposed category, confidence, and the coverage of the top clusters

#### Scenario: Applying confirmations

- **WHEN** a set of confirmations (cluster → chosen category, or skip) is applied
- **THEN** an active rule is created for each confirmed cluster and none for skipped ones

#### Scenario: Generation does not block the request

- **WHEN** proposal generation is triggered
- **THEN** the request returns promptly with a generation status, and the proposals become available as they are produced

### Requirement: Classification stats endpoint

The API SHALL expose a stats endpoint returning coverage (decided vs. total transactions), auto-apply rate (auto-applied vs. review), and the current pending-review count.

#### Scenario: Requesting stats

- **WHEN** the stats endpoint is called
- **THEN** it returns coverage, auto-apply rate, and pending-review count computed from the current data

### Requirement: Active rules endpoint

The API SHALL expose an endpoint listing the active classification rules with their pattern and target category.

#### Scenario: Listing active rules

- **WHEN** the rules endpoint is called
- **THEN** it returns the active rules with pattern and target category
