## ADDED Requirements

### Requirement: Categorization as splits summing to total

The system SHALL represent the categorization of a transaction as an ordered set of splits, each `(amount, category, evidence)`, whose amounts sum to the transaction total. A single-category result SHALL be represented as a set containing exactly one split.

#### Scenario: Single-category result

- **WHEN** a transaction is classified to one category
- **THEN** the categorization contains exactly one split whose amount equals the transaction total

#### Scenario: Multi-item split sums to total

- **WHEN** a transaction is split across multiple categories from a receipt
- **THEN** the sum of the split amounts equals the transaction total within the reconciliation tolerance

### Requirement: Evidence-backed decisions

Every applied categorization SHALL reference the evidence chain that justified it. The system SHALL NOT apply a categorization that has no supporting evidence.

#### Scenario: Decision carries its evidence

- **WHEN** a categorization is applied to a transaction
- **THEN** the persisted result includes references to the evidence objects that produced it

#### Scenario: No evidence means no auto-apply

- **WHEN** no gatherer produces evidence above the `NONE` tier for a transaction
- **THEN** the transaction is routed to human review rather than auto-applied

### Requirement: Deterministic evidence policy

The mapping from collected evidence to a categorization SHALL be a deterministic function of that evidence. Given identical evidence, the policy SHALL always produce the same decision.

#### Scenario: Deterministic given identical evidence

- **WHEN** the policy is evaluated twice on the same set of evidence
- **THEN** it produces the same categorization or the same routing-to-review outcome both times

### Requirement: Collection loop with sufficiency check

The system SHALL evaluate sufficiency of the evidence collected so far; if insufficient, it SHALL request the highest-value missing evidence from an appropriate gatherer and re-evaluate; if gatherers are exhausted without sufficiency, it SHALL route the transaction to human review. Triage SHALL be the first iteration of this loop rather than a separate stage.

#### Scenario: Known merchant resolves on first iteration

- **WHEN** a fixed-rule or history gatherer produces sufficient evidence on the first loop iteration
- **THEN** the loop terminates and the categorization is applied without invoking costlier gatherers

#### Scenario: Insufficient evidence triggers next gatherer

- **WHEN** the current evidence is below the required tier for the transaction
- **THEN** the loop invokes the next highest-value gatherer (e.g. web lookup, then receipt retrieval) before re-evaluating

#### Scenario: Exhausted gatherers route to review

- **WHEN** all applicable gatherers have run and evidence remains below the required tier
- **THEN** the transaction is routed to human review

### Requirement: Required-tier decision table

The system SHALL determine the tier required to auto-apply a claim from the transaction's context (at minimum: merchant class and whether the claim is a split), using a human-authored decision table that is separate from the tier definitions. The required-tier table SHALL be the tunable risk dial; tier definitions SHALL be authored separately.

#### Scenario: Single-category merchant auto-applies at STRONG

- **WHEN** evidence for a single-category claim reaches the `STRONG` tier required by the table for that merchant class
- **THEN** the categorization is auto-applied

#### Scenario: Splittable merchant requires itemized PROOF

- **WHEN** the merchant is in the splittable class and the available evidence is below itemized `PROOF`
- **THEN** the system does not auto-apply a split and routes the transaction to human review

### Requirement: Combination by strongest-governs

When multiple pieces of evidence are present, the system SHALL assign each candidate claim the tier of the single highest-tier evidence supporting it, and SHALL NOT promote a claim's tier by accumulating multiple lower-tier pieces. Corroboration MAY break ties within a tier but MUST NOT raise a tier.

#### Scenario: Strongest evidence wins

- **WHEN** a reconciling receipt (itemized PROOF) and a web lookup (WEAK) disagree about the categorization
- **THEN** the receipt's claim governs the decision

#### Scenario: Weak evidence does not accumulate into proof

- **WHEN** several `WEAK` pieces of evidence agree on a claim and no higher-tier evidence exists
- **THEN** the claim's tier remains `WEAK` and is not promoted to `STRONG` or `PROOF`

### Requirement: Contested claims route to review

When two or more claims tie at the highest available tier and disagree, the system SHALL treat the result as contested and route the transaction to human review rather than choosing arbitrarily.

#### Scenario: Top-tier disagreement is contested

- **WHEN** two claims are both at the highest available tier and specify different categorizations
- **THEN** the transaction is routed to human review marked as contested

### Requirement: Itemized invariant for splits

The system SHALL NOT auto-apply a split categorization unless the supporting evidence is itemized and at the `PROOF` tier. Non-itemized evidence MAY auto-apply only single-category claims.

#### Scenario: Non-itemized evidence cannot produce a split

- **WHEN** the strongest evidence for a multi-item merchant is non-itemized
- **THEN** the system does not produce an auto-applied split
