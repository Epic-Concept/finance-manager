# Change: Add Automatic Transaction Classifier

## Why

Manual transaction categorization is the biggest pain point in personal finance tools. Users must classify every transaction by hand, which is tedious and error-prone. Transactions from large retailers (Amazon, Allegro, AliExpress) are particularly problematic because the bank statement only shows the merchant name, not what was actually purchased.

This change introduces a two-subsystem automatic classifier:
1. **Deterministic Rules Engine** - Reliably classifies transactions using bank data with configurable rules
2. **AI-Powered Disambiguation** - Uses email receipts to classify ambiguous multi-category purchases

## What Changes

### New Capabilities
- **Transaction Classification** - New capability covering rules engine, AI disambiguation, and classification orchestration

### Schema Additions
- `email_accounts` table - Stores multiple email account configurations per user
- `category_evidence` table - Stores item-level classification evidence with provenance
- `classification_rules` table - Stores rules engine expressions

### New Dependencies
- `rule-engine` Python package (BSD 3-Clause) for deterministic classification
- MCP server integration (`imap-mcp`) for email access

### Architecture Additions
- `RulesClassificationService` - Evaluates rules against transactions
- `EmailSearchService` - Searches emails via MCP server
- `AIDisambiguationService` - LLM-powered receipt parsing
- `ClassificationOrchestrator` - Coordinates rules + AI services

## Impact

- **Affected specs**:
  - `database-schema` - New tables for email accounts, category evidence, classification rules
  - `transaction-classification` - New capability (to be created)

- **Affected code**:
  - `apps/api/src/finance_api/models/` - New SQLAlchemy models
  - `apps/api/src/finance_api/repositories/` - New repositories
  - `apps/api/src/finance_api/services/` - New classification services
  - `apps/api/alembic/versions/` - New migration

- **External dependencies**:
  - `rule-engine>=4.5.0` - Rules expression evaluation
  - `anthropic` Python SDK - Claude 4.5 Sonnet for receipt extraction
  - MCP server configuration for email access (imap-mcp)
