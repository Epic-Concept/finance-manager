# Tasks: Add Category Commitment Hierarchy

> **Note:** Queue-based classification (Tasks 2, 4-10) has been superseded by `add-rule-discovery` which takes an interactive rule-building approach instead. Those tasks are archived below.

## Dependencies

This change depends on `add-transaction-classifier` for:
- RulesClassificationService
- ClassificationOrchestrator

---

## 1. Database Schema - Category Extensions

- [x] 1.1 Add `commitment_level` column to Category model (Integer, nullable)
- [x] 1.2 Add `frequency` column to Category model (String(20), nullable)
- [x] 1.3 Add `is_essential` column to Category model (Boolean, default=False)
- [x] 1.4 Create Alembic migration for category column additions
- [x] 1.5 Write unit tests for new Category fields
- [x] 1.6 Run integration tests to verify migration on SQL Server

## ~~2. Database Schema - Queue Tables~~ (ARCHIVED - see add-rule-discovery)

> Superseded by `rule_proposals` table in `add-rule-discovery`

- [~] 2.1 ~~Create `ClassificationQueue` SQLAlchemy model~~
- [~] 2.2 ~~Create `ClassificationAttempt` SQLAlchemy model~~
- [~] 2.3 ~~Update `models/__init__.py` to export new models~~
- [~] 2.4 ~~Create Alembic migration for queue tables~~
- [~] 2.5 ~~Write unit tests for new models~~
- [~] 2.6 ~~Run integration tests to verify migration on SQL Server~~

## 3. Default Category Seeding

- [x] 3.1 Create category seed data based on research hierarchy (~117 categories)
- [x] 3.2 Include commitment_level and frequency for each category
- [x] 3.3 Create seed script (SQL and Python versions in apps/api/scripts/)
- [x] 3.4 Write tests to verify seed data structure
- [x] 3.5 Document category hierarchy in README

## 4. Repositories

- [x] 4.1 Extend `CategoryRepository` with methods for commitment level queries
  - [x] Method: get_by_commitment_level, get_effective_commitment_level (with inheritance)
  - [x] Method: get_by_frequency, get_essential_categories
- [x] 4.2 Write unit tests for CategoryRepository extensions (13 new tests)

## ~~5-10. Queue-Based Classification~~ (ARCHIVED)

> The following sections are superseded by `add-rule-discovery` which uses:
> - Interactive clustering + LLM rule proposals (instead of queue-based agentic processing)
> - CLI-based batch classification (instead of queue processor service)
> - `rule_proposals` table for tracking (instead of queue/attempt tables)
>
> See `add-rule-discovery` for the replacement approach.

---

## Completed

All remaining tasks for `add-category-hierarchy` have been completed:
- [x] 1.5 Unit tests for new Category fields (11 tests in `tests/models/test_category.py`)
- [x] 3.4 Seed data structure tests (16 tests in `tests/scripts/test_seed_categories.py`)
- [x] 4.1-4.2 CategoryRepository extensions (4 new methods + 13 tests)

All classification work continues in `add-rule-discovery`.
