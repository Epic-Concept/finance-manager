# Tasks: Add Transaction Classifier

## 1. Database Schema

- [x] 1.1 Create `EmailAccount` SQLAlchemy model in `apps/api/src/finance_api/models/email_account.py`
- [x] 1.2 Create `ClassificationRule` SQLAlchemy model in `apps/api/src/finance_api/models/classification_rule.py`
- [x] 1.3 Create `CategoryEvidence` SQLAlchemy model in `apps/api/src/finance_api/models/category_evidence.py`
- [x] 1.4 Update `models/__init__.py` to export new models
- [x] 1.5 Create Alembic migration for new tables (email_accounts, classification_rules, category_evidence)
- [x] 1.6 Write unit tests for new models (27 model tests)
- [ ] 1.7 Run integration tests to verify migration on SQL Server (manual verification needed)

## 2. Repositories

- [x] 2.1 Create `EmailAccountRepository` in `apps/api/src/finance_api/repositories/email_account_repository.py`
- [x] 2.2 Create `ClassificationRuleRepository` in `apps/api/src/finance_api/repositories/classification_rule_repository.py`
- [x] 2.3 Create `CategoryEvidenceRepository` in `apps/api/src/finance_api/repositories/category_evidence_repository.py`
- [x] 2.4 Write unit tests for repositories (63 repository tests)
- [x] 2.5 Write integration tests for repositories (tests use real SQLAlchemy session)

## 3. Rules Classification Service

- [x] 3.1 Add `rule-engine>=4.5.0` to `pyproject.toml` dependencies
- [x] 3.2 Create `RulesClassificationService` in `apps/api/src/finance_api/services/rules_classification_service.py`
- [x] 3.3 Implement rule loading and caching by priority
- [x] 3.4 Implement transaction-to-context mapping for rule-engine
- [x] 3.5 Implement rule evaluation with first-match-wins logic
- [x] 3.6 Write unit tests with mocked repositories (24 tests)
- [x] 3.7 Write integration tests with test rules

## 4. Email Integration

- [ ] 4.1 Document MCP server setup (imap-mcp) in README (Phase 2)
- [x] 4.2 Create `EmailSearchService` in `apps/api/src/finance_api/services/email_search_service.py`
- [x] 4.3 Implement email account iteration by priority
- [x] 4.4 Implement date-range and merchant search query building
- [x] 4.5 Write unit tests with mocked MCP client (17 tests)
- [ ] 4.6 Write integration test with test email account (manual verification needed)

## 5. AI Disambiguation Service

- [x] 5.1 Add `anthropic>=0.40.0` to `pyproject.toml` dependencies
- [x] 5.2 Create `ReceiptExtractionService` in `apps/api/src/finance_api/services/receipt_extraction_service.py`
- [x] 5.3 Implement LLM prompt template for receipt parsing (Claude claude-sonnet-4-5)
- [x] 5.4 Implement JSON response parsing and validation
- [x] 5.5 Create `CategoryMappingService` in `apps/api/src/finance_api/services/category_mapping_service.py`
- [x] 5.6 Implement item-to-category mapping logic
- [x] 5.7 Implement transaction total validation (sum of items vs transaction amount)
- [x] 5.8 Create `AIDisambiguationService` in `apps/api/src/finance_api/services/ai_disambiguation_service.py`
- [x] 5.9 Orchestrate email search, extraction, and mapping
- [x] 5.10 Implement evidence storage with full provenance
- [x] 5.11 Add confidence threshold configuration (default: 0.9)
- [x] 5.12 Write unit tests with mocked LLM responses (43+ tests)
- [x] 5.13 Write integration tests with sample receipts

## 6. Classification Orchestrator

- [x] 6.1 Create `ClassificationOrchestrator` in `apps/api/src/finance_api/services/classification_orchestrator.py`
- [x] 6.2 Implement single-transaction classification pipeline
- [x] 6.3 Implement batch classification for multiple transactions
- [x] 6.4 Implement idempotency check (skip already classified unless force=True)
- [x] 6.5 Integrate with FastAPI BackgroundTasks for async disambiguation (implemented but not separately tested)
- [x] 6.6 Write unit tests for orchestration logic (21 tests)
- [ ] 6.7 Write end-to-end integration tests (currently uses mocked services)

## 7. API Endpoints (Optional - Phase 2)

- [ ] 7.1 Create `/api/v1/classification/rules` CRUD endpoints
- [ ] 7.2 Create `/api/v1/classification/email-accounts` CRUD endpoints
- [ ] 7.3 Create `/api/v1/transactions/{id}/classify` endpoint
- [ ] 7.4 Create `/api/v1/transactions/classify-batch` endpoint
- [ ] 7.5 Write API endpoint tests

## Dependencies

- Task 2.x depends on Task 1.x (models must exist before repositories)
- Task 3.x depends on Task 2.2 (rule service needs rule repository)
- Task 4.x depends on Task 2.1 (email service needs email account repository)
- Task 5.x depends on Task 4.x (disambiguation needs email search)
- Task 6.x depends on Tasks 3.x, 5.x (orchestrator needs both services)
- Task 7.x depends on Task 6.x (endpoints need orchestrator)

## Parallelizable Work

- Tasks 1.1, 1.2, 1.3 can run in parallel (independent models)
- Tasks 2.1, 2.2, 2.3 can run in parallel after models complete
- Tasks 3.x and 4.x can run in parallel after repositories complete

## Bug Fixes Applied (January 2026)

The following bugs were identified and fixed during code review:

### CRITICAL - Fixed
- **Rule evidence not persisted**: When a rule matches without disambiguation, now creates
  evidence record with `evidence_type='rule'`, rule name/expression in `evidence_summary`,
  and `confidence_score=1.0`. (classification_orchestrator.py:127-145)

### HIGH Priority - Fixed
- **Shipping cost logic**: Now stores shipping as separate evidence row even when $0
  (free shipping). Changed condition from `> 0` to `is not None`. (ai_disambiguation_service.py:156)

### MEDIUM Priority - Fixed
- **Replace print() with logging**: Replaced `print()` statements in rules_classification_service.py
  with proper `logging.warning()` calls. (rules_classification_service.py:82-88)

### Notes
- Email date null check was already handled correctly at line 104 with `if email.date:`
- Total test count: 195+ tests covering all implemented functionality
