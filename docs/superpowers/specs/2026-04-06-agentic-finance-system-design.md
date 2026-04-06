# Agentic Finance System Design

## Summary
Design a new local-first, household-first financial operations platform with pi.dev as the core agentic orchestration engine. The system should own the workflow end-to-end: broker-based transaction ingestion, mailbox API ingestion, transaction normalization, evidence retrieval, transfer detection, classification, low-confidence review, rule suggestion, and continuous optimization via DSPy GEPA. The current codebase is a capability reference only; the new system may be built as a separate project.

## Goals
- Build a complete package that owns ingestion, decisioning, review, and improvement.
- Use pi.dev as the central orchestrator for transaction-centric workflows.
- Automate high-confidence cases and send only low-confidence cases to human review.
- Use broad email evidence, not just merchant confirmations, to support decisions.
- Detect confirmed and likely between-account transfers by looking across household accounts.
- Keep the system local-first, with optional cloud services only where useful.
- Optimize the review experience for speed.
- Keep deterministic rules approval-based, while improving agent behavior through evaluation and DSPy GEPA optimization.
- Design household-first with clean seams for later multi-tenant expansion.

## Non-Goals for the First Implementation Slice
- Full multi-tenant productization.
- Complex budgeting, reporting, or analytics beyond what supports decision quality.
- Autonomous rule promotion without explicit approval.
- Broad cloud-first deployment requirements.
- Multiple mailbox providers implemented at once.
- Perfect historical backfill before validating the new workflow.

## Recommended Architecture
Use a central pi.dev-driven orchestrator with specialist tools/agents behind it.

### Why this approach
This approach best fits the goal of making pi.dev the core engine rather than a sidecar. It provides one place to coordinate rule checks, merchant narrowing, email evidence retrieval, transfer detection, confidence scoring, explanation generation, and escalation. It also keeps the first version easier to understand than a fully event-driven worker mesh while preserving clean boundaries for future evolution.

### Alternatives considered
1. **Event-driven pipeline with agents as workers**
   - Strong for replayability and scale.
   - Rejected for v1 because of higher operational and design complexity.
2. **Deterministic core with agent assist at a few steps**
   - Strong for control and testability.
   - Rejected because it underuses pi.dev as the system core.

## High-Level Architecture
The system should be split into two layers.

### 1. Deterministic platform services
These own infrastructure and durable state:
- connectors for broker and mailbox providers
- storage and indexing
- normalization
- rules engine
- review queue
- audit and evidence persistence

### 2. Agentic decision layer
This layer is driven by pi.dev and owns:
- per-transaction workflow orchestration
- evidence gathering strategy
- specialist tool invocation
- confidence scoring
- short explanation generation
- escalation decisions

pi.dev should decide, but should not own raw connector polling, token storage, or ledger persistence.

## Core Components

### Ingestion layer
- **Broker connector**: pulls account and transaction data from the same type of third-party broker currently used via n8n.
- **Mailbox connectors**: pull email through direct provider APIs.
- **Sync scheduler**: manages polling cadence, cursors, retries, and checkpoints.
- **Normalizer**: maps provider-specific payloads into canonical records.

### Financial data core
Durable domain records should include:
- households
- users/persons
- accounts
- mailboxes
- transaction sources
- transactions
- balances/postings metadata as needed
- merchants/entities
- transfer candidates and transfer links
- classification decisions
- review decisions
- fixed rules and candidate rules

Raw source records should be preserved alongside normalized records to support reprocessing.

### Evidence and retrieval layer
This layer should support:
- email indexing
- transaction-to-email candidate linking
- merchant/entity resolution memory
- account relationship graphing
- evidence ranking

Its purpose is to narrow the space of likely explanations before the final decision step.

### pi.dev orchestration layer
For each transaction or reconciliation case, pi.dev should:
1. check fixed rules
2. narrow likely merchant/entity
3. gather supporting evidence from email and prior history
4. inspect other accounts for transfer patterns
5. decide category and/or transfer status
6. emit confidence and a short explanation
7. auto-apply or escalate to review

### Review and feedback layer
A fast review surface should support:
- low-confidence classifications
- likely transfers needing confirmation
- conflicting evidence cases
- candidate rule approvals

### Rules intelligence layer
Knowledge should exist in three forms:
- **fixed rules**: deterministic, approved, auto-applied
- **candidate rules**: suggested, awaiting explicit approval
- **heuristic signals**: reusable but non-binding guidance used by the agent system

## Per-Transaction Decision Flow

### Stage 1: deterministic checks
Run the cheapest and highest-trust logic first:
- exact or regex rule matches
- known merchant mappings
- previously confirmed recurring patterns
- known transfer templates

If a fixed rule resolves the case with strong certainty, classify immediately.

### Stage 2: merchant/entity narrowing
If deterministic logic is insufficient, the system should infer where the purchase likely occurred using:
- transaction description patterns
- amount patterns
- MCC or broker metadata when available
- previously linked merchants
- nearby email evidence
- historical household behavior

This step reduces candidate space; it does not necessarily make the final classification.

### Stage 3: evidence gathering
The email evidence agent should search broadly for supporting records, including:
- confirmations
- invoices
- shipment notices
- travel bookings
- digital purchase receipts
- subscription renewals
- other relevant commercial messages

Evidence ranking should consider:
- date proximity
- amount proximity
- merchant similarity
- sender/domain trust
- historical linkage usefulness

### Stage 4: transfer detection
The system should inspect other household accounts for:
- offsetting movements
- similar amounts within a time window
- recurring internal transfer patterns
- source/destination naming hints
- previously confirmed transfer behavior

Outcomes should be:
- confirmed transfer
- likely transfer
- not a transfer

### Stage 5: final decision
pi.dev should synthesize all gathered signals and produce:
- category or transfer designation
- confidence score or confidence band
- short explanation
- linked evidence references

### Stage 6: escalation
A case must go to review when:
- confidence is below threshold
- multiple plausible categories remain
- transfer evidence is suggestive but incomplete
- evidence conflicts
- the transaction appears novel enough to justify confirmation

## Human Review Experience
The review experience should optimize for speed. Each review item should show:
- transaction summary
- proposed classification or transfer status
- confidence band
- short explanation
- top 1-3 evidence items
- one-click actions such as approve, reclassify, mark transfer, mark not-transfer, ignore, or create rule suggestion

The default interaction should be fast confirmation/correction rather than deep investigation.

## Learning and Optimization

### Case memory and reusable signals
Reviewed outcomes should improve:
- retrieval and ranking quality
- merchant/entity linking
- transfer pairing signals
- future evidence prioritization

### Structured evaluation dataset
Reviewed outcomes should be turned into a continuously growing labeled dataset. It should include slices for:
- recurring merchants
- ambiguous merchants
- subscriptions
- transfers
- refunds
- split or compound purchases
- novel edge cases

This dataset becomes the benchmark for optimization and regression testing.

### DSPy GEPA optimization
The system should use DSPy GEPA to optimize the prompting/program behavior of the agentic decision pipeline. Optimization targets should be measured on labeled review data rather than model self-consistency.

Optimization candidates may include:
- evidence selection strategy
- context formatting
- decision rubric wording
- confidence calibration instructions
- transfer-detection reasoning structure
- merchant-resolution prompting strategy

GEPA-optimized variants must be evaluated offline on held-out household data before promotion. The system should version prompt/program variants and support reprocessing against past transactions.

### Rules remain approval-based
Even with GEPA optimization, rule promotion should remain explicit:
- the system may discover candidate rules from repeated reviewed outcomes
- fixed rules require approval before they become deterministic automation

## Safety, Auditability, and Privacy
- Raw source records must be immutable.
- Every automated decision must be versioned.
- Rule changes must be audited.
- Prompt/program variants must be versioned.
- Evidence links should be stored separately from user-facing explanations.
- Low-confidence or conflicting cases must not silently auto-apply.
- Reprocessing must be possible after rule, prompt, or model changes.
- Broker and mailbox credentials should remain local by default.
- Optional cloud services must be additive rather than required.
- Sensitive content such as raw emails should be access-controlled and exposed minimally in user-facing views.

## Proposed Technical Shape
Even if implemented in a single repository, the system should be split into logical modules/services.

### connector-service
Responsibilities:
- broker sync
- mailbox provider sync
- cursor/checkpoint management
- token handling

### ledger-service
Responsibilities:
- accounts
- transactions
- balances/postings metadata
- raw source records

### evidence-service
Responsibilities:
- email storage and indexing
- metadata extraction
- linkage candidates
- evidence ranking and retrieval

### decision-service
Responsibilities:
- rule evaluation
- transaction decision records
- confidence outputs
- short explanations

### review-service
Responsibilities:
- review queue
- corrections
- rule approvals

### optimization-service
Responsibilities:
- labeled eval dataset management
- DSPy GEPA runs
- prompt/program version registry
- offline evaluation reports

## Storage and Processing Model
- **Relational database** for operational records.
- **Optional search/index layer** for email and evidence retrieval.
- **Optional object/blob storage** for raw artifacts.
- **Append-only decision/event history** for auditability and reprocessing.

Processing should be hybrid:
- synchronous path for cheap, high-confidence decisions
- background jobs for mailbox sync, enrichment, transfer correlation, optimization runs, and bulk reprocessing

## Tenancy Model
The system should be household-first but future-friendly. The domain model should explicitly represent:
- household
- person/user
- account
- mailbox
- transaction source
- review actor

Authorization can stay simple in v1, but data boundaries should not assume a single global household.

## Scope Decomposition
The full target system is too broad to treat as one implementation chunk. The right approach is:
- one architecture/design spec for the full target system
- one first implementation plan focused on a constrained but complete vertical slice

## Recommended First Implementation Slice
1. Define foundational domain and storage for households, accounts, mailboxes, transactions, decisions, reviews, rules, and evidence links.
2. Replace the current n8n-style broker ingestion with a native ingestion path in the new system.
3. Implement one mailbox provider integration to prove direct email retrieval.
4. Build the pi.dev transaction workflow covering:
   - fixed rule check
   - merchant narrowing
   - email evidence lookup
   - transfer lookup
   - category/transfer proposal
   - confidence and short explanation
   - review escalation
5. Build a fast review queue with approve/correct/transfer actions.
6. Build the evaluation and optimization foundation so reviewed outcomes become labeled data for GEPA runs.

## Deferred from the First Slice
- multiple mailbox providers at once
- complex reporting and budgeting
- generalized product-grade multi-tenant authorization
- autonomous rule promotion
- advanced analytics/visualization
- broad cloud deployment concerns
- perfect historical backfill before validating core workflows

## First-Slice Success Criteria
A real transaction entering the new system should be able to:
- be ingested through the broker path
- exist in the canonical store
- be processed by a pi.dev workflow
- use rules, email evidence, and transfer lookup
- produce a proposed classification with confidence and short explanation
- route to review when uncertain
- feed the reviewed outcome into the optimization dataset

## Open Decisions Resolved in This Design
- Human review is required only for low-confidence cases.
- Email evidence may come from any relevant mailbox content.
- The system may emit likely-transfer suggestions when evidence is partial.
- The new system should own the workflow end-to-end, not just post-ingestion classification.
- The first implementation priority is the full platform skeleton.
- Deployment is local-first.
- Review UX is optimized for speed.
- User-facing output should include a short explanation.
- Rule suggestions require explicit approval.
- The system is household-first with future seams for multi-tenant support.
- Learning-loop optimization should use DSPy GEPA.

## Recommended Next Step
Create an implementation plan for the first vertical slice while preserving the full-system architecture described above.
