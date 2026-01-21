# Design: Add Transaction Schema

## Overview

This change introduces the core database schema for financial transaction management, including a hierarchical category system using the closure table pattern, and a repository layer for maintaining data consistency.

## Architecture Decisions

### AD-1: Finance Schema Namespace

**Decision**: Use a dedicated `finance` schema for all financial tables.

**Rationale**:
- Matches the external project structure for consistency
- Provides logical grouping of financial data
- Enables future multi-schema architecture if needed
- Cleaner separation from system tables

### AD-2: Closure Table for Category Hierarchy

**Decision**: Implement category hierarchy using the closure table pattern instead of adjacency list or nested sets.

**Rationale**:
- **Query efficiency**: All ancestors/descendants retrieved in single query
- **Roll-up support**: Easily aggregate transactions across subtrees
- **Flexibility**: Categories at any level can be linked to transactions
- **Maintenance**: Simpler than nested sets for inserts/updates

### AD-3: Separate Transaction-Category Linking Table

**Decision**: Use a dedicated `transaction_categories` table instead of a `category_id` FK on transactions.

**Rationale**:
- **Separation of concerns**: Transaction data remains independent of categorization
- **Flexibility**: Easy to change categorization without modifying transaction records
- **Auditability**: Can track when categorization was added/changed
- **Future extensibility**: Could support multiple categories per transaction if needed
- **Query pattern**: JOIN-based queries align with closure table roll-up patterns

### AD-4: Repository Pattern for Closure Table Consistency

**Decision**: Use a `CategoryRepository` with atomic methods for category operations instead of database triggers.

**Rationale**:
- **Testability**: Repository methods can be unit tested without database
- **Visibility**: Logic is in Python, easier to debug and maintain
- **Transaction control**: Explicit transaction boundaries in application code
- **Portability**: No dependency on database-specific trigger syntax

**Trade-offs**:
- All category mutations must go through the repository
- Direct SQL updates would bypass consistency checks
- Accepted: Application is the single source of truth for category operations

### AD-5: Decimal for Financial Amounts

**Decision**: Use `DECIMAL(19, 4)` for all monetary values.

**Rationale**:
- Avoids floating-point precision issues
- Industry standard for financial applications
- 4 decimal places supports currency conversion scenarios
- Matches project constraint in `project.md`

## Schema Design

### Entity Relationship

```
┌─────────────────┐
│  bank_sessions  │
└─────────────────┘

┌─────────────────┐
│online_purchases │
└─────────────────┘

┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  transactions   │◀────│ transaction_categories│────▶│   categories    │
└─────────────────┘     └─────────────────────┘     └────────┬────────┘
                                                             │
                                                             │ closure
                                                             ▼
                                                    ┌─────────────────┐
                                                    │category_closure │
                                                    └─────────────────┘
```

### Table Definitions

#### finance.bank_sessions
Stores Enable Banking session data for cached bank connections.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | PK, IDENTITY |
| bank_key | NVARCHAR(100) | NOT NULL, UNIQUE |
| bank_name | NVARCHAR(200) | NOT NULL |
| session_id | NVARCHAR(255) | NOT NULL |
| session_expires | DATETIME2 | NOT NULL |
| accounts | NVARCHAR(MAX) | NULL (JSON) |
| created_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |
| updated_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |

#### finance.transactions
Core financial transaction storage.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | PK, IDENTITY |
| transaction_date | DATE | NOT NULL |
| description | NVARCHAR(500) | NOT NULL |
| amount | DECIMAL(19,4) | NOT NULL |
| currency | NVARCHAR(3) | NOT NULL, DEFAULT 'GBP' |
| external_id | NVARCHAR(255) | NULL (for bank import dedup) |
| account_name | NVARCHAR(200) | NULL |
| notes | NVARCHAR(MAX) | NULL |
| created_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |
| updated_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |

#### finance.online_purchases
Stores online shopping purchase details for transaction matching and categorization.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | PK, IDENTITY |
| shop_name | NVARCHAR(200) | NOT NULL |
| items | NVARCHAR(MAX) | NOT NULL |
| purchase_datetime | DATETIME2 | NOT NULL |
| price | DECIMAL(19,4) | NOT NULL |
| currency | NVARCHAR(3) | NOT NULL, DEFAULT 'GBP' |
| is_deferred_payment | BIT | NOT NULL, DEFAULT 0 |
| transaction_id | INT | FK → transactions(id), NULL |
| created_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |
| updated_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |

#### finance.categories
Stores category definitions.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | PK, IDENTITY |
| name | NVARCHAR(100) | NOT NULL |
| parent_id | INT | FK → categories(id), NULL for root |
| description | NVARCHAR(500) | NULL |
| created_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |
| updated_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |

#### finance.category_closure
Closure table for category hierarchy.

| Column | Type | Constraints |
|--------|------|-------------|
| ancestor_id | INT | PK, FK → categories(id) |
| descendant_id | INT | PK, FK → categories(id) |
| depth | INT | NOT NULL |

**Notes**:
- Every category has a self-referencing row (ancestor=descendant, depth=0)
- `depth` indicates the distance between ancestor and descendant
- Enables queries like "all ancestors of X" or "all descendants of X"

#### finance.transaction_categories
Links transactions to categories.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT | PK, IDENTITY |
| transaction_id | INT | FK → transactions(id), NOT NULL, UNIQUE |
| category_id | INT | FK → categories(id), NOT NULL |
| created_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |
| updated_at | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() |

**Notes**:
- UNIQUE constraint on transaction_id enforces one category per transaction
- Separate table allows categorization to be added/changed independently

### Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| IX_bank_sessions_expires | bank_sessions | session_expires | Session cleanup queries |
| IX_transactions_date | transactions | transaction_date | Date range queries |
| IX_transactions_external | transactions | external_id | Deduplication on import |
| IX_online_purchases_datetime | online_purchases | purchase_datetime | Date range queries |
| IX_online_purchases_transaction | online_purchases | transaction_id | Transaction lookup |
| IX_category_closure_descendant | category_closure | descendant_id | Ancestor queries |
| IX_transaction_categories_category | transaction_categories | category_id | Category roll-ups |

## CategoryRepository Design

The repository encapsulates all category mutations to maintain closure table consistency.

### Interface

```python
class CategoryRepository:
    def __init__(self, session: Session): ...

    def create(self, name: str, parent_id: int | None = None, description: str | None = None) -> Category:
        """Create a category and populate closure table entries."""

    def move(self, category_id: int, new_parent_id: int | None) -> Category:
        """Move a category to a new parent, updating all closure entries."""

    def delete(self, category_id: int, cascade: bool = False) -> None:
        """Delete a category and its closure entries. Optionally cascade to children."""

    def get_ancestors(self, category_id: int) -> list[Category]:
        """Get all ancestors of a category (including self)."""

    def get_descendants(self, category_id: int) -> list[Category]:
        """Get all descendants of a category (including self)."""

    def get_subtree_transaction_sum(self, category_id: int) -> Decimal:
        """Sum all transactions in category and descendants."""
```

### Closure Table Maintenance

#### On Create
1. Insert the new category record
2. Copy all closure entries where descendant = parent_id, increment depth by 1, set descendant = new_id
3. Insert self-reference (ancestor=new_id, descendant=new_id, depth=0)

#### On Move
1. Delete all closure entries where descendant is in the subtree being moved AND ancestor is NOT in the subtree
2. For each node in the subtree, insert closure entries linking to new ancestors

#### On Delete
1. If cascade=False and has children, raise error
2. Delete closure entries where ancestor or descendant = category_id
3. Delete the category record

## SQLAlchemy Model Structure

```
apps/api/src/finance_api/
├── models/
│   ├── __init__.py
│   ├── bank_session.py
│   ├── category.py          # Category + CategoryClosure
│   ├── online_purchase.py
│   ├── transaction.py
│   └── transaction_category.py
├── repositories/
│   ├── __init__.py
│   └── category_repository.py
```

Models will:
- Use SQLAlchemy 2.0 style with `Mapped` type hints
- Inherit from the existing `Base` in `db/base.py`
- Define relationships with proper back_populates
- Include `__tablename__` with schema prefix

## Roll-up Query Pattern

With the separate linking table and closure table, aggregating transactions across a category subtree:

```sql
SELECT SUM(t.amount)
FROM finance.transactions t
JOIN finance.transaction_categories tc ON t.id = tc.transaction_id
JOIN finance.category_closure cc ON tc.category_id = cc.descendant_id
WHERE cc.ancestor_id = :category_id
```

This returns sum of all transactions in the category and all its descendants.
