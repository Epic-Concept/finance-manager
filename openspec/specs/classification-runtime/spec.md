# classification-runtime Specification

## Purpose

Production composition of the classification engine (engine factory + config for gatherers/mailboxes/categories), the `DbHistorySource` adapter, and the daily orchestration job that classifies new transactions and records decisions + review items.

## Requirements

### Requirement: Engine composition from configuration

The system SHALL provide a factory that builds a ready `ClassificationEngine` — the policy plus the configured gatherers (rules, history, web-lookup, LLM-inference, agentic-receipt) wired to their real backends (DB, Brave, local LLM, Gmail) — from configuration, without the caller assembling gatherers by hand.

#### Scenario: Factory returns a usable engine

- **WHEN** the factory is invoked with valid configuration
- **THEN** it returns a `ClassificationEngine` whose gatherers are connected to their real backends and whose policy is the deterministic evidence policy

#### Scenario: A backend that is not configured is omitted

- **WHEN** a gatherer's backend is not configured (e.g. no mailbox)
- **THEN** that gatherer is omitted and the engine still runs with the remaining gatherers

### Requirement: History evidence from persisted decisions

The system SHALL provide a `DbHistorySource` that returns prior confirmed outcomes for a merchant from the persisted decisions, so the history gatherer contributes in production.

#### Scenario: Prior confirmed category surfaces as history

- **WHEN** a merchant has prior confirmed categorizations in the store
- **THEN** `DbHistorySource` returns them as history outcomes for the history gatherer

### Requirement: Daily classification run

The system SHALL provide an orchestration job that classifies newly-synced, not-yet-classified transactions through the engine, persists each decision (with splits and the evidence chain), and enqueues review items for non-auto-applied outcomes. The job SHALL be idempotent — re-running SHALL NOT reclassify transactions already decided.

#### Scenario: New transactions are classified and recorded

- **WHEN** the daily job runs after a sync
- **THEN** each new unclassified transaction has a persisted decision, auto-applied ones carry their splits + evidence, and review-routed ones appear in the review queue

#### Scenario: Already-decided transactions are skipped

- **WHEN** the daily job runs again with no new transactions
- **THEN** it makes no new decisions
