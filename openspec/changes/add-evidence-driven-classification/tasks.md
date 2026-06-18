## 1. Evidence model and gatherer contract

- [x] 1.1 Define the `Evidence` type (claim, type, source, strength tier, `itemized` flag) and the strength tier enum (`PROOF/STRONG/WEAK/NONE`)
- [x] 1.2 Define the gatherer interface (declares producible evidence types; returns `Evidence[]`; reports honest/degraded strength)
- [x] 1.3 Add unit tests asserting gatherers never write a final categorization

## 2. Deterministic evidence policy

- [x] 2.1 Implement claim grouping and max-not-sum tier assignment per claim
- [x] 2.2 Implement the required-tier decision table as a separate, human-authored config keyed by merchant class and split-or-not
- [x] 2.3 Implement the itemized invariant (splits require itemized `PROOF`)
- [x] 2.4 Implement contested detection (top-tier disagreement → review)
- [x] 2.5 Implement the collection loop (sufficiency check → request next highest-value gatherer → re-evaluate → exhausted → review)
- [x] 2.6 Write exhaustive unit tests over evidence permutations (determinism, strongest-governs, no-accumulation, itemized invariant, contested routing)

## 3. Cheap deterministic gatherers

- [x] 3.1 Implement the description-matching rule gatherer (replaces the `rule-engine` runtime)
- [x] 3.2 Implement the history gatherer (merchant→category from prior confirmed outcomes)
- [ ] 3.3 Remove the `rule-engine` dependency and the old `RulesClassificationService`

## 4. Agentic receipt-evidence retrieval

- [ ] 4.1 Implement multi-mailbox search with merchant/amount/date-window query and one configurable widening
- [x] 4.2 Implement candidate ranking and ambiguity detection (degrade strength; report when matches found in >1 mailbox)
- [x] 4.3 Wire line-item extraction to the local LLM on `gb10.local`; ensure raw email content never leaves on-prem
- [x] 4.4 Implement total reconciliation banding (within tolerance → itemized PROOF; moderate → flagged STRONG; large → WEAK)
- [x] 4.5 Port existing receipt extraction and item→category mapping behind the gatherer contract

## 5. Web-lookup and LLM-inference gatherers

- [x] 5.1 Implement the web-lookup gatherer for unknown merchants (merchant-class signal)
- [x] 5.2 Implement the LLM-inference gatherer (bare description guess, always WEAK)

## 6. Categorization output and persistence

- [x] 6.1 Introduce first-class categorization splits (transaction → N splits summing to total within tolerance)
- [x] 6.2 Persist the evidence chain as the audit trail for every applied categorization
- [x] 6.3 Implement the review-queue routing path for insufficient/contested/ambiguous outcomes

## 7. Engine integration

- [x] 7.1 Replace `ClassificationOrchestrator` and `AIDisambiguationService` with the gather/decide engine
- [ ] 7.2 Retire redundant LLM rule-creation surfaces (`propose_rule`, `refine_rule`, `explain_pattern`), keeping one conversational refinement tool for the review/learning loop
- [x] 7.3 Add a shadow-mode runner that classifies historical transactions and reports parity vs the old path before cutover

## 8. Asynchronous shadow learner

- [x] 8.1 Emit confirmed `(evidence → decision)` outcomes as an event stream off the hot path
- [x] 8.2 Implement rule proposal from consistent confirmed outcomes with stability criteria requiring ≥1 human confirmation
- [x] 8.3 Implement cache asymmetry (single-category mappings cacheable; variable splits not, except exact recurring charges)
- [x] 8.4 Enforce the learning boundary: gatherer/prompt optimization allowed; policy-gate recalibration only via surfaced, human-approved change

## 9. Verification

- [ ] 9.1 End-to-end tests for known-merchant fast path, multi-item receipt split, no-receipt review routing, and double-receipt ambiguity
- [ ] 9.2 Demonstrate shadow-mode parity before removing the legacy classification path
