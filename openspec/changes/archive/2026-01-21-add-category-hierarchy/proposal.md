# Change: Add Category Commitment Hierarchy and Classification Queue

## Why

Transaction classification requires more than just matching rules - it needs context about what each category represents in terms of financial commitment. The current category system is flat in terms of meaning: there's no way to distinguish between "must pay or face eviction" expenses (rent) and "nice to have" expenses (streaming subscriptions).

Additionally, when automatic classification fails, transactions currently have no clear path to resolution. We need a structured queue that tracks unclassifiable transactions and enables an agentic workflow to research them via email receipts and web searches.

This change introduces:
1. **Commitment Level Hierarchy** - 5-tier system (L0-L4) for categorizing expenses by flexibility
2. **Classification Queue** - Tracks transactions pending classification with status and resolution attempts
3. **Agentic Classification Workflow** - Multi-source research flow using emails and web to identify purchases

## What Changes

### Schema Additions
- `commitment_level` column on `categories` - Integer 0-4 indicating flexibility
- `frequency` column on `categories` - Expense timing (monthly, quarterly, annual, irregular)
- `is_essential` column on `categories` - User override for essential status
- `classification_queue` table - Tracks transactions pending classification
- `classification_attempt` table - Logs resolution attempts with sources tried

### New Capabilities
- **Category Hierarchy** - Commitment level metadata on categories
- **Classification Queue Management** - Track, prioritize, and resolve unclassifiable transactions
- **Agentic Research Workflow** - Multi-step flow: rules → email search → web search → manual

### Builds Upon
- `add-transaction-classifier` change (rules engine, email integration, AI disambiguation)

## Impact

- **Affected specs**:
  - `database-schema` - New columns on categories, new queue tables
  - `category-hierarchy` - New capability (to be created)

- **Affected code**:
  - `apps/api/src/finance_api/models/category.py` - Add new columns
  - `apps/api/src/finance_api/models/` - New ClassificationQueue, ClassificationAttempt models
  - `apps/api/src/finance_api/services/` - New QueueManagementService, AgenticClassificationService
  - `apps/api/alembic/versions/` - New migration

- **Dependencies**:
  - Requires `add-transaction-classifier` to be implemented first (rules engine, email search)
  - Uses MCP servers: `imap-mcp` (email), web search capability

## Reference Documents

- `openspec/design-docs/budgeting-and-affordability-research.md` - Full research on category hierarchies and affordability algorithms
