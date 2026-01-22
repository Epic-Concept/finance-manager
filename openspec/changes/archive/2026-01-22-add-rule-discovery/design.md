# Design: Rule Discovery System

## Overview

The Rule Discovery System enables incremental, intelligent creation of classification rules from historical transaction data. It addresses the cold-start problem of having thousands of uncategorized transactions with no rules.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RULE DISCOVERY WORKFLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CLUSTER ANALYSIS                                             │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │ Load uncategorized transactions from DB                  │ │
│     │ Normalize descriptions (uppercase, remove store IDs)     │ │
│     │ Cluster by token similarity                              │ │
│     │ Rank clusters by size (most prevalent first)             │ │
│     └─────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  2. RULE PROPOSAL (LLM-powered)                                  │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │ Show cluster samples + category list to LLM              │ │
│     │ LLM proposes: regex pattern + category + confidence      │ │
│     │ Test pattern against ALL transactions                    │ │
│     │ Calculate precision, false positives                     │ │
│     └─────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  3. USER REVIEW (Interactive CLI)                                │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │ Accept rule → Save to classification_rules               │ │
│     │ Modify rule → Re-test and save                           │ │
│     │ Reject rule → Mark as rejected, skip                     │ │
│     └─────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  4. APPLY & ITERATE                                              │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │ Run classification with approved rules                   │ │
│     │ Update coverage statistics                               │ │
│     │ Re-cluster remaining uncategorized                       │ │
│     └─────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Clustering method** | Token-based | Fast, deterministic, good for structured bank descriptions. Extracts first significant token after normalization. |
| **Persist proposals** | Yes (DB) | Track all LLM proposals for audit trail, resumability, and pattern analysis |
| **Auto-accept rules** | No | Always require manual review for maximum control over classification quality |
| **LLM model** | Claude claude-sonnet-4-5 | Fast, cost-effective for structured JSON generation |

## Component Design

### 1. TransactionClusteringService

**Purpose:** Group similar transactions by description patterns

**Normalization Pipeline:**
```
Original:      "TESCO STORES 1234"
1. Uppercase:  "TESCO STORES 1234"
2. Strip nums: "TESCO STORES"
3. Remove suffix: "TESCO"
4. Result:     Cluster key = "TESCO"
```

**Removable Suffixes:** STORES, STORE, LTD, S.A., LIMITED, INC, ORDER, PAYMENT, EXPRESS

**Clustering Algorithm:**
1. Normalize all descriptions
2. Extract first significant token (longest non-suffix word)
3. Group by normalized token
4. Calculate cluster cohesion (description variance within cluster)
5. Split clusters with low cohesion

### 2. RuleDiscoveryService

**Purpose:** Use LLM to propose rules from clusters

**Prompt Template:**
```
You are a transaction classification expert. Given these sample transactions
from a cluster of similar items:

{sample_descriptions}

And this category hierarchy:
{category_list}

Propose a classification rule:
1. A regex pattern (Python re syntax) that matches these transactions
2. The most appropriate category from the list
3. Confidence level (high/medium/low)
4. Brief reasoning

Respond in JSON format:
{
  "pattern": "(?i)tesco",
  "category_name": "Groceries - Basic",
  "confidence": "high",
  "reasoning": "All transactions appear to be Tesco supermarket purchases"
}
```

### 3. RuleValidationService

**Purpose:** Test rules against all transactions before approval

**Metrics Calculated:**
- `matches`: Total transactions matching the pattern
- `true_positives`: Matches within the target cluster
- `false_positives`: Matches outside the target cluster
- `precision`: TP / (TP + FP)
- `coverage`: TP / cluster_size

**Conflict Detection:** Check if new rule overlaps with existing rules

### 4. Interactive CLI (discover_rules.py)

**User Flow:**
```
=== Transaction Rule Discovery ===

Loading transactions... 1,933 total, 1,800 uncategorized

Clustering transactions...
Found 47 clusters (covering 89% of transactions)

=== Cluster #1: 234 transactions (13.0%) ===
Normalized: "TESCO"
Samples:
  - TESCO STORES 1234
  - TESCO EXPRESS
  - tesco.com

Proposing rule via LLM...
Pattern: description =~ "(?i)tesco"
Category: Groceries - Basic (Level 0)
Precision: 100% (234 matches, 0 false positives)

[A]ccept  [M]odify  [R]eject  [S]kip  [Q]uit: _
```

## Data Model

### RuleProposal Table

```sql
CREATE TABLE finance.rule_proposals (
    id INT IDENTITY(1,1) PRIMARY KEY,
    cluster_hash VARCHAR(64) NOT NULL,
    cluster_size INT NOT NULL,
    sample_descriptions TEXT NOT NULL,          -- JSON array
    proposed_pattern VARCHAR(500),
    proposed_category_id INT,
    llm_confidence VARCHAR(20),
    llm_reasoning TEXT,
    validation_matches INT,
    validation_precision DECIMAL(5,4),
    validation_false_positives TEXT,            -- JSON array
    status VARCHAR(20) DEFAULT 'pending',       -- pending/accepted/rejected/modified
    created_at DATETIME2 DEFAULT GETDATE(),
    reviewed_at DATETIME2,
    final_rule_id INT,                          -- FK if accepted
    reviewer_notes TEXT
);
```

**Status Flow:**
```
pending → accepted → (linked to classification_rules)
        → rejected → (preserved for audit)
        → modified → accepted → (linked with modified pattern)
```

## Trade-offs Considered

### Embedding-based Clustering (Rejected)
- **Pro:** Better semantic similarity
- **Con:** Slower, requires embedding model, overkill for structured bank descriptions
- **Decision:** Start with token-based, add embeddings later if needed

### Auto-Accept High Confidence (Rejected)
- **Pro:** Faster rule creation
- **Con:** Risk of silent false positives, less user control
- **Decision:** Always require review; speed up review UX instead

### Batch LLM Calls (Deferred)
- **Pro:** Process multiple clusters in one call
- **Con:** More complex prompt, harder to debug
- **Decision:** Start with single-cluster calls, optimize if latency is problematic
