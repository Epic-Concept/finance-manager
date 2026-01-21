# Design: Category Commitment Hierarchy and Classification Queue

## Context

The finance manager needs to understand not just WHAT category a transaction belongs to, but HOW FLEXIBLE that expense is. This enables future affordability calculations ("Can I afford X?") and helps users understand their financial commitments.

Additionally, automatic classification will fail for some transactions. Rather than silently leaving them uncategorized, we need a structured workflow that:
1. Tracks what's been tried
2. Progressively escalates research efforts
3. Knows when to give up and flag for manual classification

**Stakeholders**: End users who want accurate categorization; system operators who need visibility into classification failures.

**Constraints**:
- Must work with real transaction data in existing SQL database
- Must integrate with existing `add-transaction-classifier` services
- Must support graceful degradation (if email search fails, try web; if web fails, queue for manual)
- Must not overwhelm external services (rate limiting, batching)

## Goals / Non-Goals

### Goals
- Assign commitment levels (0-4) to all categories
- Seed default category hierarchy based on research
- Track transactions that fail automatic classification
- Implement agentic workflow: rules → email → web → manual
- Provide clear visibility into queue status and resolution attempts
- "Stand down" gracefully when classification isn't possible

### Non-Goals
- Real-time classification (batch processing for now)
- User-facing queue management UI (API only for MVP)
- Integration with OCR for receipt images (text-based only)
- Multi-user queue isolation (single-user per project.md)

## Decisions

### Decision 1: Commitment Level Schema

**Choice**: Integer column (0-4) on categories table

**Rationale**:
- Simple, queryable, sortable
- Allows future granularity (could add 0.5 levels if needed)
- Maps directly to research framework

**Levels**:
| Level | Name | Description |
|-------|------|-------------|
| 0 | SURVIVAL | Non-negotiable (rent, utilities, minimum debt) |
| 1 | COMMITTED | Contractual (insurance, phone, childcare) |
| 2 | LIFESTYLE | Adjustable with effort (grocery quality, gym) |
| 3 | DISCRETIONARY | Easily cut (dining, entertainment, hobbies) |
| 4 | FUTURE | Savings goals (emergency fund, retirement) |

### Decision 2: Classification Queue Model

**Choice**: Separate `classification_queue` table with status tracking

**Rationale**:
- Clear separation from transactions (not all transactions need queue entries)
- Enables audit trail of attempts
- Supports priority ordering and batch processing

**Schema**:
```
classification_queue:
  id: INT PK
  transaction_id: INT FK UNIQUE
  status: ENUM (pending, in_progress, resolved, manual_required, skipped)
  priority: INT (lower = more urgent)
  created_at: DATETIME
  updated_at: DATETIME
  resolved_at: DATETIME NULL
  resolution_source: VARCHAR (rule, email, web, manual) NULL
  notes: TEXT NULL
```

### Decision 3: Classification Attempt Tracking

**Choice**: `classification_attempt` table logging each research attempt

**Rationale**:
- Full audit trail for debugging
- Prevents re-trying failed approaches
- Enables learning from patterns

**Schema**:
```
classification_attempt:
  id: INT PK
  queue_id: INT FK
  attempt_type: ENUM (rule, email_search, web_search, ai_inference)
  started_at: DATETIME
  completed_at: DATETIME NULL
  success: BOOLEAN
  result_summary: TEXT NULL
  error_message: TEXT NULL
  raw_response: NVARCHAR(MAX) NULL
```

### Decision 4: Agentic Workflow Design

**Choice**: Sequential pipeline with early exit on success

```
┌─────────────────────────────────────────────────────────────────┐
│                   AgenticClassificationService                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. RULES ENGINE (from add-transaction-classifier)              │
│     ├── Match found + high confidence → RESOLVED                │
│     └── No match OR low confidence → continue                   │
│                                                                  │
│  2. EMAIL SEARCH (via MCP - imap-mcp)                           │
│     ├── Search merchant + date range                            │
│     ├── Found receipt → extract items → RESOLVED                │
│     └── No email found → continue                               │
│                                                                  │
│  3. WEB SEARCH (merchant identification)                        │
│     ├── Search company name                                      │
│     ├── Identify business type → infer category → RESOLVED      │
│     └── Ambiguous results → continue                            │
│                                                                  │
│  4. MANUAL QUEUE                                                 │
│     └── Mark as manual_required, stand down                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Rationale**:
- Sequential reduces API costs (stop when successful)
- Each step has clear success/failure criteria
- "Stand down" is explicit state, not silent failure

### Decision 5: Web Search Integration

**Choice**: Use WebSearch tool via Claude Code or dedicated MCP server

**Rationale**:
- Company name → business type mapping is reliable
- Example: "AMZN MKTP" → search → "Amazon Marketplace" → category: Shopping
- Falls back gracefully if search fails

**Search Strategy**:
```python
def identify_merchant(description: str) -> MerchantInfo:
    # 1. Extract likely merchant name from description
    merchant_name = extract_merchant_name(description)

    # 2. Search web for company info
    search_results = web_search(f"{merchant_name} company what do they sell")

    # 3. Use LLM to extract business type
    business_type = llm_extract_business_type(search_results)

    # 4. Map business type to category
    return map_business_to_category(business_type)
```

### Decision 6: Queue Processing Strategy

**Choice**: Batch processing with configurable limits

**Rationale**:
- Respects rate limits on external services
- Allows prioritization (oldest first, or by amount)
- Can be triggered manually or scheduled

**Parameters**:
- `batch_size`: 10 (default)
- `max_attempts_per_item`: 3
- `cooldown_between_batches`: 60 seconds

### Decision 7: Category Seeding

**Choice**: Provide default category hierarchy as migration data

**Rationale**:
- Users shouldn't start with empty categories
- Research-backed structure provides good defaults
- Users can customize after seeding

**Approach**:
1. Migration creates ~50 default categories
2. Each has name, parent_id, commitment_level, frequency
3. User's existing categories (if any) are preserved, can be mapped

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transaction Ingestion                         │
│              (from bank sync or manual entry)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              ClassificationOrchestrator                          │
│         (from add-transaction-classifier)                       │
│                            │                                     │
│              ┌─────────────┴─────────────┐                      │
│              ▼                           ▼                       │
│  ┌───────────────────┐       ┌───────────────────────────┐      │
│  │ Direct Assignment │       │   Queue for Research       │     │
│  │ (Rules matched)   │       │   (Rules failed)          │     │
│  └───────────────────┘       └───────────────────────────┘      │
└──────────────────────────────────────────┼──────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              QueueManagementService                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - Create queue entries for unclassified transactions   │    │
│  │  - Track status and attempts                            │    │
│  │  - Prioritize queue                                     │    │
│  │  - Report on queue health                               │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────┼──────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              AgenticClassificationService                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Step 1: Try rules again (maybe new rules added)        │    │
│  │          └── Success? → Resolve and exit                │    │
│  │                                                         │    │
│  │  Step 2: Email search (via EmailSearchService)          │    │
│  │          └── Receipt found? → Extract → Resolve         │    │
│  │                                                         │    │
│  │  Step 3: Web search (merchant identification)           │    │
│  │          └── Company identified? → Infer → Resolve      │    │
│  │                                                         │    │
│  │  Step 4: Mark as manual_required, stand down            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

### Modified: categories

| Column | Type | Purpose | New? |
|--------|------|---------|------|
| commitment_level | INT | 0-4 hierarchy level | YES |
| frequency | VARCHAR(20) | monthly, quarterly, annual, irregular | YES |
| is_essential | BOOLEAN | User override for essential status | YES |

### New: classification_queue

| Column | Type | Purpose |
|--------|------|---------|
| id | INT PK | Primary key |
| transaction_id | INT FK UNIQUE | Linked transaction |
| status | VARCHAR(20) | pending, in_progress, resolved, manual_required, skipped |
| priority | INT | Lower = more urgent |
| created_at | DATETIME | When queued |
| updated_at | DATETIME | Last status change |
| resolved_at | DATETIME | When resolved (null if pending) |
| resolution_source | VARCHAR(20) | rule, email, web, manual (null if pending) |
| notes | TEXT | Human-readable notes |

### New: classification_attempt

| Column | Type | Purpose |
|--------|------|---------|
| id | INT PK | Primary key |
| queue_id | INT FK | Linked queue entry |
| attempt_type | VARCHAR(20) | rule, email_search, web_search, ai_inference |
| started_at | DATETIME | When attempt started |
| completed_at | DATETIME | When attempt finished |
| success | BOOLEAN | Did this attempt resolve? |
| result_summary | TEXT | Human-readable summary |
| error_message | TEXT | Error details if failed |
| raw_response | NVARCHAR(MAX) | Full response for debugging |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Web search rate limiting | Implement backoff, batch processing, caching of company info |
| Category seeding conflicts with existing data | Make seeding optional, provide mapping tool |
| Queue grows unbounded | Dashboard alerts, auto-skip after N attempts |
| Commitment levels subjective | Provide sensible defaults, allow user override |
| External service downtime | Graceful degradation, retry later |

## Migration Plan

1. **Phase 1: Schema** - Add columns to categories, create queue tables
2. **Phase 2: Seeding** - Populate default category hierarchy with commitment levels
3. **Phase 3: Queue Service** - Implement QueueManagementService
4. **Phase 4: Agentic Flow** - Implement AgenticClassificationService
5. **Phase 5: Integration** - Wire into ClassificationOrchestrator

**Rollback**: Each phase is independent. Queue tables can be dropped without affecting core functionality.

## Open Questions

None - all resolved based on research document.
