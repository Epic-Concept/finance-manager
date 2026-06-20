## Why

Transaction classification is the core of this product, but the current implementation has accreted three generations of thinking (a `rule-engine` DSL classifier, a receipt-splitting AI path, and four overlapping LLM rule-creation surfaces) that tangle *gathering* information with *deciding* on it. The result is ~3,500 LOC across 12 services where the decision logic is hard to test, hard to explain, and hard to extend.

We are rebuilding the classification core around a single principle: **every categorization decision must be a deterministic function of typed evidence.** A transaction resolves to one category or a split across several; cheap deterministic rules handle the obvious cases, while an agentic workflow (running against a local LLM on `gb10.local`, with mailbox access) gathers receipt evidence for the non-obvious, multi-item cases. Separating messy, agentic *evidence gathering* from a deterministic *evidence policy* makes the decision layer exhaustively testable and gives every decision a native audit trail.

## What Changes

- **NEW** A categorization is always a set of splits `[(amount, category, evidence), ...]` that sum to the transaction total. Single-category is the degenerate `N=1` case — there is no separate "splitting subsystem".
- **NEW** A uniform `Evidence` type (claim, type, source, strength tier, `itemized` flag) emitted by all gatherers. Gatherers never make final decisions; they only produce evidence.
- **NEW** Pluggable **evidence gatherers**: fixed rules / memory, history, web lookup (agentic), receipt hunt across household mailboxes (agentic + local LLM), and LLM inference. Some deterministic, some agentic — all behind one interface.
- **NEW** A deterministic **evidence policy**: a collection loop (evaluate sufficiency → fetch highest-value missing evidence → repeat → else review) plus a decision table over evidence tiers (`PROOF / STRONG / WEAK / NONE`). Combination is **max-not-sum**; ties that disagree are contested → review; a split claim *always* requires itemized `PROOF`.
- **NEW** Receipt hunting across **multiple household mailboxes** with hardcoded time-window heuristics; ambiguity (e.g. a matching receipt in two mailboxes) degrades evidence strength rather than forcing a guess.
- **NEW** A separate, async **shadow learner** that observes confirmed `(evidence → decision)` pairs and proposes new deterministic rules, promoting only when stable. It improves gatherers/prompts but never silently changes the policy gate.
- **BREAKING** Removes the `rule-engine` DSL classifier and its expression-based rules; rules become description-matching evidence gatherers, not a runtime DSL.
- **BREAKING** Replaces the branchy `ClassificationOrchestrator` (with its many `method` strings) and the standalone `AIDisambiguationService` flow with the gather/decide architecture.
- Retires the redundant LLM rule-creation surfaces (`propose_rule`, `refine_rule`, `explain_pattern`), keeping a single conversational refinement tool scoped to the human-review/learning loop.

## Capabilities

### New Capabilities
- `transaction-classification`: The gather/decide engine — the collection loop, the deterministic evidence policy (tiers, required-tier table, combination rules, the itemized invariant), and how a transaction resolves to a categorization (splits summing to total) with confidence and an evidence chain.
- `evidence-model`: The first-class `Evidence` type and the gatherer contract — evidence claim/type/source/strength/itemized, the strength tier ordering, and how gatherers (rules, history, web lookup, receipt hunt, LLM inference) emit evidence without deciding.
- `receipt-evidence-retrieval`: The agentic receipt-hunting workflow — searching across household mailboxes within time windows, candidate ranking, line-item extraction via the local LLM, total reconciliation banding, and honest ambiguity reporting.
- `classification-learning`: The async shadow learner — observing confirmed outcomes, proposing/promoting deterministic rules, the asymmetry between cacheable merchant→category mappings and non-cacheable splits, and the boundary that learning optimizes gatherers but never the human-owned policy gate.

### Modified Capabilities
<!-- None: OpenSpec specs were not previously captured in openspec/specs/; this is a greenfield rebuild of the classification core. -->

## Impact

- **Affected code (rebuilt or removed):** `services/classification_orchestrator.py`, `services/rules_classification_service.py`, `services/ai_disambiguation_service.py`, `services/rule_discovery_service.py`, `services/transaction_clustering_service.py`, `services/rule_validation_service.py`, `services/high_frequency_analyzer.py`, `services/interactive_refinement_service.py`, `services/category_mapping_service.py`, `services/email_search_service.py`, `services/receipt_extraction_service.py`.
- **Dependencies:** removes `rule-engine`; introduces a local LLM client targeting `gb10.local`; retains the Anthropic client only where a cloud model is explicitly chosen.
- **Data model:** categorization becomes one-to-many (transaction → N categorized splits); evidence is persisted as the audit trail (supersedes the current `category_evidence` usage as a first-class concept).
- **Privacy posture:** raw mailbox content is read only by the on-prem local LLM, never sent to a cloud provider.
- **Carried forward from existing code:** receipt extraction, item→category mapping, total reconciliation, the deterministic cache (formerly "rules"), cheap-before-expensive ordering, and human approval before a rule sticks.
- **Out of scope / deferred:** exact tier *definitions*, the money-at-risk gate shape, the double-receipt household disambiguator, and any cloud/Azure deployment concerns (the system is local-first).
