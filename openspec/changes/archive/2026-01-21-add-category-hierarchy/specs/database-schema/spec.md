## MODIFIED Requirements

### Requirement: Category Hierarchy
Categories MUST support hierarchical organization using the closure table pattern, and MUST include commitment level metadata for budgeting and affordability calculations.

#### Scenario: Category table structure
- Given the finance schema exists
- When the categories table is created
- Then it contains columns for id, name, parent_id, description, commitment_level, frequency, is_essential, created_at, updated_at
- And parent_id references categories(id)
- And commitment_level is an integer (0-4) nullable
- And frequency is a varchar(20) nullable with values: monthly, quarterly, semi_annual, annual, irregular
- And is_essential is a boolean defaulting to false

#### Scenario: Closure table structure
- Given the categories table exists
- When the category_closure table is created
- Then it contains columns for ancestor_id, descendant_id, depth
- And both ancestor_id and descendant_id reference categories(id)
- And (ancestor_id, descendant_id) forms the composite primary key

#### Scenario: Ancestor query
- Given a category hierarchy with parent → child → grandchild
- When querying ancestors of grandchild
- Then the result includes parent, child, and grandchild (self)
- And depth values are 2, 1, and 0 respectively

#### Scenario: Commitment level inheritance
- Given a parent category with commitment_level 1
- When a child category has commitment_level NULL
- Then the effective commitment level is inherited from the parent
- And categories with explicit values override inheritance

## ADDED Requirements

### Requirement: Classification Queue Storage
The system MUST track transactions that require classification with status and resolution metadata.

#### Scenario: Classification queue table structure
- Given the finance schema exists
- When the classification_queue table is created
- Then it contains columns for id, transaction_id, status, priority, created_at, updated_at, resolved_at, resolution_source, notes
- And transaction_id references transactions(id) with a unique constraint
- And status is varchar(20) with values: pending, in_progress, resolved, manual_required, skipped
- And resolution_source is varchar(20) nullable with values: rule, email, web, manual
- And an index exists on status for queue processing

#### Scenario: Queue entry creation
- Given a transaction that cannot be classified by rules
- When adding to the classification queue
- Then a queue entry is created with status 'pending'
- And priority defaults to 100 (medium)
- And created_at is set to current timestamp

#### Scenario: Queue resolution
- Given a pending queue entry
- When the transaction is successfully classified
- Then status is updated to 'resolved'
- And resolved_at is set to current timestamp
- And resolution_source indicates how it was resolved

### Requirement: Classification Attempt Tracking
The system MUST log each classification attempt for audit and debugging.

#### Scenario: Classification attempt table structure
- Given the finance schema exists
- When the classification_attempt table is created
- Then it contains columns for id, queue_id, attempt_type, started_at, completed_at, success, result_summary, error_message, raw_response
- And queue_id references classification_queue(id)
- And attempt_type is varchar(20) with values: rule, email_search, web_search, ai_inference
- And raw_response uses NVARCHAR(MAX) for large JSON storage

#### Scenario: Recording an attempt
- Given a queue entry being processed
- When an email search is attempted
- Then a classification_attempt record is created
- And started_at is set when processing begins
- And completed_at is set when processing ends
- And success indicates whether classification was achieved

#### Scenario: Multiple attempts per queue entry
- Given a queue entry with failed rule matching
- When email search also fails
- Then multiple attempt records exist for the same queue_id
- And each records its own attempt_type and outcome
