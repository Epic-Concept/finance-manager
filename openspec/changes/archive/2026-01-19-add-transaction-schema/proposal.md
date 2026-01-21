# Proposal: Add Transaction Schema

## Why

The application needs a database schema to store financial transaction data. The user has an existing schema design from another project that captures bank sessions for future bank polling integration. Additionally, a category system is needed for organizing and analyzing transactions with hierarchical roll-up capabilities. Online purchase data needs to be tracked separately for detailed categorization.

## What Changes

1. **Finance Schema**: Create a `finance` schema to namespace all financial tables
2. **Bank Sessions Table**: Migrate `bank_sessions` table from external project for future bank integration
3. **Transactions Table**: Core table for storing financial transactions
4. **Online Purchases Table**: Stores online shopping purchase details for transaction matching
5. **Categories Table**: Hierarchical category storage using closure table pattern
6. **Category Closure Table**: Supports ancestor/descendant queries for roll-ups
7. **Transaction Categories Table**: Links transactions to categories (separate table, not FK on transactions)
8. **CategoryRepository**: Application-layer pattern for maintaining closure table consistency

## Scope

- SQLAlchemy models for all tables
- Alembic migrations to create schema and tables
- CategoryRepository for atomic closure table operations
- No API endpoints (data layer only)
- No CSV import logic (separate feature)
- No bank polling (separate feature)

## Impact

| Area | Impact |
|------|--------|
| Database | New schema and 6 tables |
| Models | New SQLAlchemy models in `finance_api/models/` |
| Repositories | New CategoryRepository in `finance_api/repositories/` |
| Migrations | New Alembic migrations |
| Tests | Model and repository unit tests |

## Dependencies

- Requires: `local-database` spec (SQL Server + Alembic setup)
