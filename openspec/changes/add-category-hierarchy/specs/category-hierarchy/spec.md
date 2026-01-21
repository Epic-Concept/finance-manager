## ADDED Requirements

### Requirement: Commitment Level System
Categories MUST support a 5-tier commitment level hierarchy to indicate expense flexibility.

#### Scenario: Level 0 - Survival expenses
- Given a category for rent or mortgage
- When commitment_level is set to 0
- Then the category represents non-negotiable expenses
- And skipping these would cause severe consequences (eviction, credit damage)

#### Scenario: Level 1 - Committed expenses
- Given a category for insurance or phone
- When commitment_level is set to 1
- Then the category represents contractual obligations
- And these could be reduced but require significant effort

#### Scenario: Level 2 - Lifestyle expenses
- Given a category for gym membership or premium groceries
- When commitment_level is set to 2
- Then the category represents adjustable expenses
- And these can be reduced with lifestyle changes

#### Scenario: Level 3 - Discretionary expenses
- Given a category for dining out or entertainment
- When commitment_level is set to 3
- Then the category represents pure wants
- And these can be cut immediately without hardship

#### Scenario: Level 4 - Future/Savings
- Given a category for emergency fund or retirement
- When commitment_level is set to 4
- Then the category represents savings goals
- And skipping hurts future, not present

### Requirement: Default Category Seeding
The system MUST provide a default category hierarchy with commitment levels on initialization.

#### Scenario: Seeding on fresh database
- Given no categories exist
- When the seeding migration runs
- Then approximately 50 default categories are created
- And each has appropriate name, parent_id, commitment_level, and frequency
- And the hierarchy follows the research-backed structure (Housing, Utilities, Food, etc.)

#### Scenario: Seeding preserves existing categories
- Given categories already exist from previous use
- When the seeding migration runs
- Then existing categories are not deleted or modified
- And new default categories are added with different IDs
- And users can manually merge or map if desired

### Requirement: Classification Queue Management
The system MUST manage a queue of transactions requiring classification research.

#### Scenario: Queue population from classifier
- Given transactions fail rule-based classification
- When the ClassificationOrchestrator processes them
- Then queue entries are created for unclassified transactions
- And status is set to 'pending'
- And the orchestrator returns immediately (async processing)

#### Scenario: Queue prioritization
- Given multiple pending queue entries
- When processing the queue
- Then entries are processed in priority order (lower number = higher priority)
- And within same priority, older entries are processed first

#### Scenario: Queue health reporting
- Given queue entries in various states
- When requesting queue status
- Then counts are returned for each status (pending, in_progress, resolved, manual_required, skipped)
- And average resolution time is calculated
- And oldest pending entry age is reported

### Requirement: Agentic Classification Workflow
The system MUST implement a multi-step workflow to classify difficult transactions.

#### Scenario: Step 1 - Rules re-evaluation
- Given a queue entry for an unclassified transaction
- When agentic processing begins
- Then rules are re-evaluated (new rules may have been added)
- And if a match is found, the entry is resolved with source 'rule'
- And processing stops

#### Scenario: Step 2 - Email search
- Given rules did not classify the transaction
- When email search is attempted
- Then all configured email accounts are searched
- And search uses merchant name and date range (±7 days)
- And if a receipt is found, items are extracted and category is assigned
- And the entry is resolved with source 'email'

#### Scenario: Step 3 - Web search for merchant identification
- Given email search did not find a receipt
- When web search is attempted
- Then the merchant name from the transaction is searched
- And the business type is identified (e.g., "Amazon" → "Online Retailer")
- And a category is inferred from business type
- And the entry is resolved with source 'web'

#### Scenario: Step 4 - Stand down for manual classification
- Given all automated methods failed
- When no category can be determined
- Then the queue entry status is set to 'manual_required'
- And no further automatic attempts are made
- And the system "stands down" gracefully

#### Scenario: Attempt logging
- Given any classification attempt (rule, email, web)
- When the attempt completes
- Then a classification_attempt record is created
- And it includes attempt_type, success, and result_summary
- And failed attempts include error_message

### Requirement: Batch Queue Processing
The system MUST support batch processing of the classification queue.

#### Scenario: Batch size limiting
- Given 100 pending queue entries
- When processing with batch_size=10
- Then only 10 entries are processed in one batch
- And the remaining 90 stay pending for future batches

#### Scenario: Cooldown between batches
- Given a batch completes processing
- When the next batch is triggered
- Then at least cooldown_seconds (default: 60) have passed
- And this prevents overwhelming external services

#### Scenario: Max attempts per item
- Given a queue entry has been attempted 3 times (max_attempts)
- When processing the queue
- Then the entry is skipped (status='skipped')
- And no further attempts are made
- And notes indicate "max attempts reached"

### Requirement: Essential Override
Users MUST be able to override the default essential status of categories.

#### Scenario: Marking a category as essential
- Given Internet category defaults to is_essential=false (Level 1)
- When a remote worker marks it as essential
- Then is_essential is set to true
- And the category is treated as Level 0 for affordability calculations

#### Scenario: Removing essential override
- Given a category has is_essential=true override
- When the user clears the override
- Then is_essential reverts to false
- And the category uses its original commitment_level
