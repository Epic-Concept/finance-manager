# Change: Add Rule Discovery System

## Why

With ~2000 uncategorized transactions, manually creating classification rules is impractical. Users need a systematic way to:
- Discover patterns in their transaction data
- Generate rules that cover common merchants/patterns
- Validate that rules don't over-match (false positives)
- Incrementally build rules while tracking progress

This change introduces an intelligent rule discovery system that clusters similar transactions, uses LLM to propose classification rules, and provides an interactive workflow for rule approval.

## What Changes

### New Capabilities
- **Rule Discovery** - New capability covering transaction clustering, LLM-powered rule proposals, validation, and interactive CLI

### Schema Additions
- `rule_proposals` table - Tracks proposed rules, validation results, and approval status for audit trail and resumability

### Architecture Additions
- `TransactionClusteringService` - Groups similar transactions by normalized description patterns
- `RuleDiscoveryService` - Uses LLM to propose rules from transaction clusters
- `RuleValidationService` - Tests proposed rules against all transactions, calculates precision metrics
- `discover_rules.py` CLI - Interactive workflow for reviewing and approving rules
- `classify_batch.py` CLI - Batch classification script with coverage reporting

## Impact

- **Depends on**: `add-transaction-classifier` (requires ClassificationOrchestrator, RulesClassificationService, ClassificationRuleRepository)
- **Supersedes**: Queue-based classification from `add-category-hierarchy` (Tasks 2, 4-10) - this proposal takes an interactive rule-building approach instead of a queue-based agentic system

- **Affected specs**:
  - `database-schema` - New rule_proposals table
  - `rule-discovery` - New capability (to be created)

- **Affected code**:
  - `apps/api/src/finance_api/models/` - New RuleProposal model
  - `apps/api/src/finance_api/repositories/` - New RuleProposalRepository
  - `apps/api/src/finance_api/services/` - New clustering, discovery, validation services
  - `apps/api/src/finance_api/scripts/` - New CLI scripts
  - `apps/api/alembic/versions/` - New migration for rule_proposals

- **External dependencies**:
  - `anthropic` Python SDK (already present from transaction-classifier)
  - No new external dependencies required
