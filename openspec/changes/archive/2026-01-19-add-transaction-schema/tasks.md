# Tasks: Add Transaction Schema

## Section 1: SQLAlchemy Models
- [x] Create `apps/api/src/finance_api/models/__init__.py` module
- [x] Create `apps/api/src/finance_api/models/bank_session.py` with BankSession model
- [x] Create `apps/api/src/finance_api/models/category.py` with Category and CategoryClosure models
- [x] Create `apps/api/src/finance_api/models/transaction.py` with Transaction model
- [x] Create `apps/api/src/finance_api/models/online_purchase.py` with OnlinePurchase model
- [x] Create `apps/api/src/finance_api/models/transaction_category.py` with TransactionCategory model
- [x] Update `db/base.py` to import all models for Alembic discovery

## Section 2: Alembic Migrations
- [x] Create migration `002_create_finance_schema.py` to create finance schema
- [x] Create migration `003_create_tables.py` to create all tables with indexes

## Section 3: Category Repository
- [x] Create `apps/api/src/finance_api/repositories/__init__.py` module
- [x] Create `apps/api/src/finance_api/repositories/category_repository.py` with:
  - [x] `create()` method with closure table population
  - [x] `move()` method with closure table updates
  - [x] `delete()` method with cascade option
  - [x] `get_ancestors()` method
  - [x] `get_descendants()` method
  - [x] `get_subtree_transaction_sum()` method

## Section 4: Model Tests
- [x] Create `apps/api/tests/models/__init__.py`
- [x] Create `apps/api/tests/models/test_bank_session.py`
- [x] Create `apps/api/tests/models/test_category.py`
- [x] Create `apps/api/tests/models/test_transaction.py`
- [x] Create `apps/api/tests/models/test_online_purchase.py`
- [x] Create `apps/api/tests/models/test_transaction_category.py`

## Section 5: Repository Tests
- [x] Create `apps/api/tests/repositories/__init__.py`
- [x] Create `apps/api/tests/repositories/test_category_repository.py` with tests for:
  - [x] Creating root category
  - [x] Creating child category with closure entries
  - [x] Moving category updates closure entries
  - [x] Deleting category cleans up closure entries
  - [x] Get ancestors returns correct hierarchy
  - [x] Get descendants returns correct hierarchy
  - [x] Subtree transaction sum aggregates correctly

## Section 6: Verification
- [x] Run migrations locally to verify schema creation
- [x] Run all tests to verify models and repository work correctly
- [x] Verify CI passes with new migrations
