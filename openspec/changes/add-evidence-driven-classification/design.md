## Context

The classification core is the product's holy grail and has accreted three generations of design: a `rule-engine` DSL classifier, an AI receipt-splitting path, and several overlapping LLM rule-creation surfaces (~3,500 LOC, 12 services). The recurring problem is that *gathering* information and *deciding* on it are tangled together, which makes the decision logic hard to test, explain, and extend. A v2 design spec already declares the current code a "capability reference only" for a greenfield rebuild.

Key constraints from the problem owner:
- Per-line-item categorization (splitting one charge across categories from a receipt) is a **core goal**, not a nice-to-have.
- Rules only need **description matching** — no compound DSL logic is required.
- A **local LLM on `gb10.local`** is available: inference is effectively free and, crucially, privacy-safe, which is what makes reading raw mailboxes to find receipts acceptable.
- The household shares accounts and **multiple mailboxes**; the paying person is not always known up front.
- The solution is **self-hosted on `gb10.local`** with **PostgreSQL** as the data store, co-located with the LLM. The classification core assumes Postgres (not SQL Server); the actual platform/DB migration is tracked as a separate infrastructure change.

## Goals / Non-Goals

**Goals:**
- A classification core where every decision is a deterministic function of typed evidence, with the evidence chain serving as the native audit trail.
- A clean separation between messy/agentic **evidence gathering** and a deterministic, exhaustively testable **evidence policy**.
- A uniform output model: categorization is always a set of splits summing to the total (single-category is `N=1`).
- An agentic receipt-retrieval workflow across household mailboxes using the local LLM.
- A separate async learning loop that turns confirmed outcomes into deterministic rules.

**Non-Goals:**
- Final tier *definitions* (what exactly makes evidence PROOF vs STRONG) — deferred; tunable once the framework exists.
- The money-at-risk gate shape and the double-receipt disambiguator — deferred edge decisions.
- Cloud/Azure deployment — the system is local-first.
- Transfer detection, budgeting, and reporting beyond what supports decision quality.

## Decisions

### Decision: Separate gathering from deciding
Two layers with different characters. **Gatherers** (rules, history, web lookup, receipt hunt, LLM inference) are allowed to be flaky, agentic, and probabilistic; they only emit `Evidence`. The **policy** is a pure, deterministic function over evidence. *Alternative considered:* a single free-roaming agent that owns the whole decision — rejected for being non-deterministic, hard to test, and prone to over-fetching. The deterministic ladder with the LLM as a scoped tool gives ~90% of the flexibility with far less chaos.

### Decision: Strength as discrete tiers, not a scalar threshold
Strength is `PROOF > STRONG > WEAK > NONE`, not a float compared to a magic threshold. A scalar conflates four independent things (provenance, match quality, completeness, corroboration) and produces unexplainable "we applied because score was 0.86" decisions. Tiers make every decision sayable and make the policy a finite, exhaustively testable table. *Alternative considered:* continuous confidence with a tunable cutoff — rejected as false precision.

### Decision: Two separate knobs — tier definitions vs required-tier table
"How good is this evidence" (tier definitions; structural, authored once) is kept distinct from "how good do I need it to be here" (required-tier table; the risk dial, the thing actually tuned). This lets risk posture change without redefining evidence meaning. Required tier is a function of context (merchant class, split-or-not, later amount).

### Decision: Combine by max-not-sum; contested → review
Each claim takes the tier of its single strongest supporting evidence; lower-tier pieces never accumulate into a higher tier. Corroboration breaks ties within a tier but never promotes one. Top-tier disagreement is contested and routed to review. This prevents the system from ever auto-applying something with no single pointable reason — the cases where accumulation tempts you are exactly the cases that should go to review.

### Decision: Itemized invariant for splits
A split is only auto-applied on itemized `PROOF` (a reconciling receipt). This single rule stops large multi-item charges from being dumped into one wrong category and neutralizes plausible-but-hallucinated LLM splits (itemized but only WEAK).

### Decision: Receipt strength from reconciliation bands
Receipt tier is set by how well line items reconcile to the total: within tolerance → itemized PROOF; moderate mismatch → flagged STRONG; large mismatch → WEAK (wrong email). Reconciliation doubles as a free wrong-receipt/mismatch detector.

### Decision: Learning is a separate async subsystem with a hard boundary
The shadow learner observes confirmed `(evidence → decision)` pairs, proposes deterministic rules, and promotes only on stability criteria that include human confirmation. It may optimize gatherers/prompts (the DSPy/GEPA seam) but never silently touches the policy gate. Single-category merchant mappings are cacheable; variable splits are not (except exact recurring charges).

### Decision: Drop `rule-engine`; rules become description-matching gatherers
Since only description matching is needed, the DSL dependency is removed. Rule-like logic returns one level up as deterministic policy over evidence facts, which is the right altitude for it.

## Risks / Trade-offs

- **No-receipt majority** → Most real transactions (rent, transit, salary, cash) have no receipt and land below itemized PROOF. Mitigation: single-category claims auto-apply at STRONG via history/rules; the rest go to review and feed the learner so the cache grows. This must be designed for explicitly, not treated as an edge case.
- **Self-confirmation feedback loop** → If STRONG could be built purely from prior auto-applies, the system could entrench its own mistakes. Mitigation: promotion requires at least one human-confirmed outcome.
- **Receipt-hunt latency/cost blowup** → The mailbox search loop could run long or over-fetch. Mitigation: bounded date windows (one widening), candidate caps, and honest ambiguity reporting instead of exhaustive search.
- **Review queue overload at cold start** → Before the cache is warm, many transactions route to review. Mitigation: the learner promotes quickly for consistent single-category merchants; seed with obvious deterministic rules.
- **Local LLM availability** → `gb10.local` being down stalls the agentic path. Mitigation: cheap deterministic gatherers still resolve known merchants; unresolved transactions queue for review rather than failing.

## Migration Plan

1. Build the `Evidence` type and gatherer contract first; port the existing receipt extraction, item→category mapping, and total reconciliation behind it.
2. Build the deterministic policy (collection loop, tier comparison, required-tier table, combination rules, itemized invariant) with exhaustive unit tests over evidence permutations.
3. Wrap existing rules as a description-matching gatherer; retire the `rule-engine` runtime.
4. Build the multi-mailbox receipt gatherer against the local LLM.
5. Add the async shadow learner last, consuming the confirmed-outcome event stream.
6. Replace `ClassificationOrchestrator` / `AIDisambiguationService` with the gather/decide engine; remove redundant LLM rule-creation surfaces, keeping one conversational refinement tool for the review/learning loop.
7. Data model: introduce first-class categorization splits (transaction → N splits) and evidence persistence.

Rollback: the gather/decide engine can run in shadow mode against historical transactions and be compared to existing classifications before cutover; the old path remains available until parity is demonstrated.

## Open Questions

- **Tier definitions**: exact criteria for PROOF/STRONG/WEAK (e.g. how many consistent prior outcomes make history STRONG; reconciliation band thresholds). Deferred — tune once the framework exists.
- **Money-at-risk gate**: absolute amount threshold vs relative-to-merchant/category anomaly. A large weekly grocery shop should not trip the same wire as a large charge from an unseen merchant.
- **Double-receipt disambiguation**: is there a deterministic disambiguator (card last-4, account holder on the charge, exact amount match) or is it always a human call?
- **No-receipt single-category fallback**: when an unknown merchant has no receipt, do we auto-apply a STRONG history/web-lookup claim or always review the first occurrence?
- **Local model choice and structured-output contract** on `gb10.local` for extraction and triage.
