# Tasks: Add Category Commitment Hierarchy and Classification Queue

## Dependencies

This change depends on `add-transaction-classifier` for:
- RulesClassificationService
- EmailSearchService
- ReceiptExtractionService
- ClassificationOrchestrator

Tasks 1-3 can proceed in parallel with `add-transaction-classifier`.
Tasks 4-5 require `add-transaction-classifier` to be implemented.

---

## 1. Database Schema - Category Extensions

- [ ] 1.1 Add `commitment_level` column to Category model (Integer, nullable)
- [ ] 1.2 Add `frequency` column to Category model (String(20), nullable)
- [ ] 1.3 Add `is_essential` column to Category model (Boolean, default=False)
- [ ] 1.4 Create Alembic migration for category column additions
- [ ] 1.5 Write unit tests for new Category fields
- [ ] 1.6 Run integration tests to verify migration on SQL Server

## 2. Database Schema - Queue Tables

- [ ] 2.1 Create `ClassificationQueue` SQLAlchemy model in `apps/api/src/finance_api/models/classification_queue.py`
- [ ] 2.2 Create `ClassificationAttempt` SQLAlchemy model in `apps/api/src/finance_api/models/classification_attempt.py`
- [ ] 2.3 Update `models/__init__.py` to export new models
- [ ] 2.4 Create Alembic migration for queue tables
- [ ] 2.5 Write unit tests for new models
- [ ] 2.6 Run integration tests to verify migration on SQL Server

## 3. Default Category Seeding

- [ ] 3.1 Create category seed data based on research hierarchy (~50 categories)
- [ ] 3.2 Include commitment_level and frequency for each category
- [ ] 3.3 Create seed migration that inserts defaults (idempotent - skip if categories exist)
- [ ] 3.4 Write tests to verify seed data structure
- [ ] 3.5 Document category hierarchy in README or design doc

## 4. Repositories

- [ ] 4.1 Create `ClassificationQueueRepository` in `apps/api/src/finance_api/repositories/classification_queue_repository.py`
  - [ ] Methods: create, get_by_id, get_by_transaction_id, get_pending, update_status, get_queue_stats
- [ ] 4.2 Create `ClassificationAttemptRepository` in `apps/api/src/finance_api/repositories/classification_attempt_repository.py`
  - [ ] Methods: create, get_by_queue_id, get_latest_attempt
- [ ] 4.3 Extend `CategoryRepository` with methods for commitment level queries
  - [ ] Method: get_by_commitment_level, get_effective_commitment_level (with inheritance)
- [ ] 4.4 Write unit tests for repositories
- [ ] 4.5 Write integration tests for repositories

## 5. Queue Management Service

- [ ] 5.1 Create `QueueManagementService` in `apps/api/src/finance_api/services/queue_management_service.py`
- [ ] 5.2 Implement `enqueue_transaction(transaction_id, priority)` method
- [ ] 5.3 Implement `get_next_batch(batch_size)` method with priority ordering
- [ ] 5.4 Implement `mark_resolved(queue_id, source, notes)` method
- [ ] 5.5 Implement `mark_manual_required(queue_id, notes)` method
- [ ] 5.6 Implement `get_queue_health()` method returning stats
- [ ] 5.7 Implement `skip_stale_entries(max_attempts)` method
- [ ] 5.8 Write unit tests with mocked repositories
- [ ] 5.9 Write integration tests

## 6. Agentic Classification Service

- [ ] 6.1 Create `AgenticClassificationService` in `apps/api/src/finance_api/services/agentic_classification_service.py`
- [ ] 6.2 Implement `process_queue_entry(queue_id)` orchestrating all steps
- [ ] 6.3 Implement Step 1: Re-evaluate rules (using RulesClassificationService)
- [ ] 6.4 Implement Step 2: Email search (using EmailSearchService + ReceiptExtractionService)
- [ ] 6.5 Implement Step 3: Web search for merchant identification
  - [ ] Extract merchant name from transaction description
  - [ ] Search web for company information
  - [ ] Use LLM to classify business type
  - [ ] Map business type to category
- [ ] 6.6 Implement Step 4: Stand down (mark as manual_required)
- [ ] 6.7 Implement attempt logging for each step
- [ ] 6.8 Write unit tests with mocked services
- [ ] 6.9 Write integration tests with sample transactions

## 7. Batch Processing

- [ ] 7.1 Create `QueueProcessorService` in `apps/api/src/finance_api/services/queue_processor_service.py`
- [ ] 7.2 Implement `process_batch(batch_size, max_attempts)` method
- [ ] 7.3 Implement cooldown logic between batches
- [ ] 7.4 Implement configurable batch parameters (batch_size, cooldown_seconds, max_attempts)
- [ ] 7.5 Write unit tests
- [ ] 7.6 Write integration tests

## 8. Integration with ClassificationOrchestrator

- [ ] 8.1 Modify `ClassificationOrchestrator` to enqueue unclassified transactions
- [ ] 8.2 Add configuration flag to enable/disable queue-based processing
- [ ] 8.3 Write integration tests for full flow: ingest → rules → queue → agentic → resolved

## 9. API Endpoints (Optional - Phase 2)

- [ ] 9.1 Create `/api/v1/classification/queue` GET endpoint (list queue entries)
- [ ] 9.2 Create `/api/v1/classification/queue/{id}` GET endpoint (single entry with attempts)
- [ ] 9.3 Create `/api/v1/classification/queue/{id}/resolve` POST endpoint (manual resolution)
- [ ] 9.4 Create `/api/v1/classification/queue/process` POST endpoint (trigger batch processing)
- [ ] 9.5 Create `/api/v1/classification/queue/stats` GET endpoint (queue health)
- [ ] 9.6 Write API endpoint tests

## 10. Scripts for Real Data Testing

- [ ] 10.1 Create script to analyze existing transactions and identify unclassified ones
- [ ] 10.2 Create script to populate queue with existing unclassified transactions
- [ ] 10.3 Create script to run agentic processing on queue
- [ ] 10.4 Create script to report classification success rates
- [ ] 10.5 Document scripts usage in README

---

## Task Dependencies

```
1.x ─────────┐
             ├──► 4.x ──► 5.x ──► 7.x ──► 8.x ──► 9.x
2.x ─────────┤                    │
             │                    ▼
3.x ─────────┘              6.x (requires add-transaction-classifier)
                                  │
                                  ▼
                               10.x
```

## Parallelizable Work

- Tasks 1.x, 2.x, 3.x can run in parallel (independent schema changes)
- Tasks 4.1, 4.2, 4.3 can run in parallel after schema (independent repositories)
- Tasks 5.x and 6.x can run in parallel after repositories (independent services)
- Task 6.x requires `add-transaction-classifier` services to be available
