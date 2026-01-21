# Tasks: Add Rule Discovery System

## Prerequisites
- `add-transaction-classifier` change must be complete (ClassificationOrchestrator, RulesClassificationService, ClassificationRuleRepository)

---

## 1. Database Schema

- [x] 1.1 Create `RuleProposal` SQLAlchemy model in `apps/api/src/finance_api/models/rule_proposal.py`
- [x] 1.2 Update `models/__init__.py` to export RuleProposal
- [x] 1.3 Create Alembic migration `006_create_rule_proposals.py`
- [x] 1.4 Write unit tests for RuleProposal model (13 tests)

## 2. Repository

- [x] 2.1 Create `RuleProposalRepository` in `apps/api/src/finance_api/repositories/rule_proposal_repository.py`
- [x] 2.2 Implement CRUD operations (create, get_by_id, get_by_status, update_status)
- [x] 2.3 Implement `get_pending_proposals()` for resume functionality
- [x] 2.4 Implement `get_by_cluster_hash()` to avoid duplicate proposals
- [x] 2.5 Write unit tests for repository (24 tests)

## 3. Transaction Clustering Service

- [x] 3.1 Create `TransactionClusteringService` in `apps/api/src/finance_api/services/transaction_clustering_service.py`
- [x] 3.2 Implement description normalization (uppercase, remove store IDs, strip suffixes)
- [x] 3.3 Implement token extraction (first significant word)
- [x] 3.4 Implement `cluster_transactions()` method returning list of Cluster dataclasses
- [x] 3.5 Implement `get_cluster_statistics()` for coverage reporting
- [x] 3.6 Implement cluster ranking by size
- [x] 3.7 Write unit tests with sample transaction data (37 tests)

## 4. Rule Validation Service

- [x] 4.1 Create `RuleValidationService` in `apps/api/src/finance_api/services/rule_validation_service.py`
- [x] 4.2 Implement `test_rule()` method that tests pattern against all transactions
- [x] 4.3 Implement precision/recall calculation
- [x] 4.4 Implement false positive sampling (return N sample FPs for review)
- [x] 4.5 Implement `find_conflicts()` to detect overlap with existing rules
- [x] 4.6 Write unit tests (32 tests)

## 5. Rule Discovery Service (LLM Integration)

- [x] 5.1 Create `RuleDiscoveryService` in `apps/api/src/finance_api/services/rule_discovery_service.py`
- [x] 5.2 Implement LLM prompt template for rule proposal
- [x] 5.3 Implement JSON response parsing and validation
- [x] 5.4 Implement `propose_rule()` method that returns RuleProposal
- [x] 5.5 Implement `refine_rule()` for iterating on rejected proposals
- [x] 5.6 Add configuration for LLM model and temperature
- [x] 5.7 Write unit tests with mocked LLM responses (18 tests)

## 6. CLI Scripts

- [x] 6.1 Create `discover_rules.py` in `apps/api/src/finance_api/scripts/`
- [x] 6.2 Implement cluster display with samples
- [x] 6.3 Implement LLM rule proposal integration
- [x] 6.4 Implement validation result display
- [x] 6.5 Implement Accept/Modify/Reject/Skip flow
- [x] 6.6 Implement `--analyze-only` mode (clustering without LLM)
- [x] 6.7 Implement `--resume` mode (continue from pending proposals)
- [x] 6.8 Create `classify_batch.py` for running classification
- [x] 6.9 Implement `--stats-only` mode for coverage reporting
- [x] 6.10 Write integration tests for CLI flows (18 tests)

## 7. Documentation

- [x] 7.1 Add rule discovery section to apps/api/README.md
- [x] 7.2 Document CLI commands and options
- [x] 7.3 Document typical workflow for building rules

---

## Dependencies

- Task 2.x depends on Task 1.x (repository needs model)
- Task 3.x can run in parallel with Tasks 1-2 (no DB dependency)
- Task 4.x can run in parallel with Tasks 1-2 (no DB dependency)
- Task 5.x depends on Task 4.x (uses validation service)
- Task 6.x depends on Tasks 2-5 (CLI integrates all services)
- Task 7.x can run in parallel once implementation is stable

## Parallelizable Work

- Tasks 1.1-1.4 (schema) can run in parallel with Tasks 3.1-3.7 (clustering)
- Tasks 3.x and 4.x are independent (can run in parallel)
- Documentation (7.x) can begin once design is stable
