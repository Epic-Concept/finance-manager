# Design: Transaction Classification System

## Context

The finance manager needs automatic transaction categorization to reduce manual effort. Bank transactions contain limited information (date, description, amount, merchant name) that is often insufficient for accurate categorization, especially for large retailers selling items across multiple categories.

**Stakeholders**: End users who want hands-off categorization; system operators who need audit trails.

**Constraints**:
- Must support enterprise-grade audit requirements (full provenance)
- Must handle multi-item purchases without splitting transactions (splitting deferred to future)
- Must support multiple email accounts per user
- Must be extensible to different email providers

## Goals / Non-Goals

### Goals
- Classify 80%+ of transactions automatically via rules
- Disambiguate remaining transactions using email receipts
- Store full evidence chain for all AI-assisted classifications
- Support multiple email accounts from day one
- Prepare data model for future transaction splitting

### Non-Goals
- Transaction splitting (out of scope, future work)
- Real-time email monitoring (batch processing only)
- OCR of attached receipt images (email text only for MVP)
- Multi-user support (single-user initially, per project.md)

## Decisions

### Decision 1: Rules Engine Selection

**Choice**: `rule-engine` Python package

**Rationale**:
- Most mature option (7 years, 34 releases, ~52K weekly downloads)
- Pythonic expression syntax reduces learning curve
- BSD 3-Clause license is business-friendly
- Thread-safe for concurrent classification
- Optional type system catches errors before execution

**Alternatives Considered**:
- **Arta (YAML-based)**: More recent activity, YAML config for non-technical editing. Rejected because smaller community (57 stars) and project needs developer-friendly expressions over YAML editing.
- **Custom implementation**: Full control but significant development effort. Rejected as premature optimization.

**Example Rule Expression**:
```python
# Match Amazon UK transactions
'description =~ "(?i)amazon\\.co\\.uk" and amount < 0'

# Match grocery stores
'description =~ "(?i)(tesco|sainsbury|asda|lidl|aldi)" and amount < 0'

# Match specific account
'account_name == "Joint Account" and description =~ "(?i)mortgage"'
```

### Decision 2: MCP Server for Email Access

**Choice**: `imap-mcp` (IMAP protocol)

**Rationale**:
- Provider-agnostic (works with Gmail, Outlook, any IMAP server)
- Full IMAP protocol support for searching and reading
- Active maintenance with learning capabilities
- Supports attachment access for future enhancement

**Alternatives Considered**:
- **Gmail-MCP-Server**: Gmail-specific, simpler auth but locks into single provider
- **email-reader-mcp**: Lighter weight but fewer features

### Decision 3: Multi-Item Transaction Handling

**Choice**: Store items in `category_evidence`, assign dominant category to transaction

**Rationale**:
- `category_evidence` stores one row per item (prepares for future splitting)
- `TransactionCategory` maintains 1:1 constraint (dominant category)
- Full item breakdown preserved for audit and future features
- No schema changes to existing `TransactionCategory` required

**Future Path**: Transaction splitting will create multiple `Transaction` records from single bank transaction, each linked to corresponding `category_evidence` rows.

### Decision 4: LLM for Receipt Extraction

**Choice**: Claude 4.5 Sonnet (`claude-sonnet-4-5-20250514`)

**Rationale**:
- Strong structured output capabilities (JSON extraction)
- Good balance of capability and cost
- Consistent with potential future Claude Code integrations

### Decision 5: Background Processing

**Choice**: FastAPI BackgroundTasks (MVP), migrate to Celery if needed

**Rationale**:
- Built into FastAPI, zero additional infrastructure
- Sufficient for single-user personal finance use case
- Simple to implement and debug
- Clear migration path to Celery if scale demands it

### Decision 6: Confidence Threshold

**Choice**: 0.9 (configurable)

**Rationale**:
- High threshold ensures quality auto-classifications
- Stored in configuration, adjustable without code changes
- Can be tuned based on real-world performance data

### Decision 7: Credential Management

**Choice**: External reference pattern (vault path or environment variable name for MVP)

**Rationale**:
- Never store actual credentials in database
- Supports multiple secret management approaches (env vars for dev, vault for prod)
- `credential_reference` column stores the reference, not the secret

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transaction Ingestion                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               ClassificationOrchestrator                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. RulesClassificationService                          │    │
│  │     - Load active rules ordered by priority             │    │
│  │     - Evaluate using rule-engine                        │    │
│  │     - Match → direct assignment OR queue for AI         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│              ┌─────────────┴─────────────┐                      │
│              ▼                           ▼                       │
│  ┌───────────────────┐       ┌───────────────────────────┐      │
│  │ Direct Assignment │       │   AI Disambiguation Queue  │     │
│  │ (TransactionCat.) │       │   (Background Worker)      │     │
│  └───────────────────┘       └───────────────────────────┘      │
│                                          │                       │
└──────────────────────────────────────────┼──────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               AIDisambiguationService                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. EmailSearchService (via MCP - imap-mcp)             │    │
│  │     - Search all configured email accounts              │    │
│  │     - Date range: transaction_date ± 7 days             │    │
│  │     - Query: merchant + "order" OR "receipt"            │    │
│  │                                                         │    │
│  │  2. ReceiptExtractionService (LLM)                      │    │
│  │     - Parse email body for order details                │    │
│  │     - Extract: items, prices, shipping, total           │    │
│  │     - Return structured JSON                            │    │
│  │                                                         │    │
│  │  3. CategoryMappingService                              │    │
│  │     - Map extracted items to categories                 │    │
│  │     - Validate total matches transaction amount         │    │
│  │     - Store evidence in category_evidence               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

### email_accounts
| Column | Type | Purpose |
|--------|------|---------|
| id | INT PK | Primary key |
| email_address | VARCHAR(255) UNIQUE | Email address |
| display_name | VARCHAR(100) | Friendly name |
| provider | VARCHAR(50) | gmail, outlook, imap_generic |
| imap_server | VARCHAR(255) | Server hostname |
| imap_port | INT | Port (default 993) |
| credential_reference | VARCHAR(500) | Vault path or env var name |
| is_active | BOOLEAN | Enable/disable |
| priority | INT | Search order |

### classification_rules
| Column | Type | Purpose |
|--------|------|---------|
| id | INT PK | Primary key |
| name | VARCHAR(100) | Human-readable name |
| rule_expression | TEXT | rule-engine expression |
| category_id | INT FK | Target category |
| priority | INT | Evaluation order (lower = first) |
| requires_disambiguation | BOOLEAN | Queue for AI after match |
| is_active | BOOLEAN | Enable/disable |

### category_evidence
| Column | Type | Purpose |
|--------|------|---------|
| id | INT PK | Primary key |
| transaction_id | INT FK | Linked transaction |
| item_description | VARCHAR(500) | Item name |
| item_price | DECIMAL(19,4) | Item price |
| item_currency | VARCHAR(3) | Currency code |
| item_quantity | INT | Quantity |
| category_id | INT FK | Item category |
| evidence_type | VARCHAR(50) | email, manual, rule, ai_inferred |
| email_account_id | INT FK | Source email account |
| email_message_id | VARCHAR(255) | Email Message-ID header |
| email_datetime | DATETIME | Email timestamp |
| evidence_summary | TEXT | Human-readable summary |
| confidence_score | DECIMAL(5,4) | AI confidence (0-1) |
| model_used | VARCHAR(100) | LLM model identifier |
| raw_extraction | NVARCHAR(MAX) | Full LLM JSON output |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Email access failures (rate limits, auth) | Retry with exponential backoff; graceful degradation to rules-only |
| LLM extraction errors | Store raw output for debugging; confidence threshold for auto-accept |
| Item total doesn't match transaction | Flag for manual review; allow tolerance for currency conversion |
| Rule conflicts (multiple matches) | Priority ordering; first match wins |
| Performance at scale | Background processing; batch LLM calls |

## Migration Plan

1. **Phase 1: Schema** - Add new tables via Alembic migration
2. **Phase 2: Rules Engine** - Implement rules service (no external dependencies)
3. **Phase 3: Email Integration** - Configure MCP server, implement email search
4. **Phase 4: AI Disambiguation** - Implement LLM extraction and evidence storage
5. **Phase 5: Orchestration** - Wire together with background processing

**Rollback**: Each phase is independent. Tables can exist without services using them.

## Resolved Questions

1. **LLM Provider**: Claude 4.5 Sonnet (`claude-sonnet-4-5-20250514`) for receipt extraction
2. **Background Processing**: FastAPI BackgroundTasks for MVP (simpler, no additional infrastructure; can migrate to Celery later if scale requires)
3. **Confidence Threshold**: 0.9 (configurable, can be adjusted based on real-world performance)
