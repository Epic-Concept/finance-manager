# transaction-classification Specification

## Purpose
Automatic classification of financial transactions using a two-subsystem approach: deterministic rules engine for reliable classification, and AI-powered disambiguation for ambiguous multi-category purchases.

## ADDED Requirements

### Requirement: Rules-Based Classification
The system MUST classify transactions using configurable rules evaluated by a rules engine.

#### Scenario: Simple rule match
- **GIVEN** a classification rule exists with expression `description =~ "(?i)tesco"` targeting category "Groceries"
- **WHEN** a transaction with description "TESCO STORES 1234" is classified
- **THEN** the transaction is assigned to category "Groceries"
- **AND** a transaction_categories record is created

#### Scenario: Rule priority ordering
- **GIVEN** rule A with priority 1 matches transactions containing "amazon"
- **AND** rule B with priority 2 matches transactions containing "amazon.co.uk"
- **WHEN** a transaction with description "AMAZON.CO.UK" is classified
- **THEN** rule A is applied (lower priority number = higher precedence)

#### Scenario: No rule match
- **GIVEN** no classification rules match a transaction
- **WHEN** the transaction is classified
- **THEN** the transaction remains uncategorized
- **AND** it is queued for AI disambiguation if AI disambiguation is enabled

#### Scenario: Rule requires disambiguation
- **GIVEN** a classification rule has requires_disambiguation set to true
- **WHEN** the rule matches a transaction
- **THEN** the transaction is assigned the rule's category
- **AND** the transaction is queued for AI disambiguation to gather evidence

### Requirement: Email Account Management
The system MUST support multiple email accounts for purchase receipt retrieval.

#### Scenario: Add email account
- **GIVEN** a user wants to add an email account
- **WHEN** they provide email_address, provider, and credential_reference
- **THEN** the email account is stored
- **AND** the account can be used for receipt retrieval

#### Scenario: Email account validation
- **GIVEN** an email account configuration exists
- **WHEN** the system attempts to connect
- **THEN** connection success or failure is reported
- **AND** credentials are never logged or exposed

#### Scenario: Email account priority
- **GIVEN** multiple email accounts exist with different priorities
- **WHEN** searching for purchase receipts
- **THEN** accounts are searched in ascending priority order
- **AND** search stops when a matching receipt is found

### Requirement: AI-Powered Disambiguation
The system MUST use AI to disambiguate transactions that cannot be fully classified by rules.

#### Scenario: Email receipt search
- **GIVEN** a transaction requires disambiguation
- **AND** email accounts are configured
- **WHEN** AI disambiguation is triggered
- **THEN** the system searches emails within 7 days of the transaction date
- **AND** searches for order confirmations or receipts from the merchant

#### Scenario: Receipt extraction
- **GIVEN** a matching email receipt is found
- **WHEN** the receipt is processed
- **THEN** the LLM extracts item names, prices, quantities, and shipping cost
- **AND** the extraction result is returned as structured JSON

#### Scenario: Multi-item purchase
- **GIVEN** an email receipt contains multiple items in different categories
- **WHEN** the receipt is processed
- **THEN** each item is stored as a separate row in category_evidence
- **AND** each item is assigned its own category
- **AND** shipping cost is stored as a separate row with description "Shipping"
- **AND** the transaction's final category is the category of the highest-value item

#### Scenario: No receipt found
- **GIVEN** a transaction requires disambiguation
- **AND** no matching email receipt is found
- **WHEN** AI disambiguation completes
- **THEN** the transaction remains with its rule-assigned category (if any)
- **AND** no category_evidence rows are created
- **AND** the transaction is flagged for manual review

### Requirement: Evidence Provenance
The system MUST store full provenance for all AI-assisted classifications.

#### Scenario: Email evidence storage
- **GIVEN** a transaction is classified using email receipt data
- **WHEN** evidence is stored
- **THEN** category_evidence records include the email account, message ID, and datetime
- **AND** evidence_summary contains a human-readable description
- **AND** confidence_score reflects the LLM's certainty
- **AND** raw_extraction stores the complete LLM output

#### Scenario: Rule evidence storage
- **GIVEN** a transaction is classified by a rule without AI disambiguation
- **WHEN** evidence is stored
- **THEN** evidence_type is set to 'rule'
- **AND** evidence_summary contains the rule name and expression
- **AND** confidence_score is 1.0 (deterministic)

### Requirement: Classification Orchestration
The system MUST orchestrate the classification process across rules and AI services.

#### Scenario: Classification pipeline
- **GIVEN** a new transaction is ingested
- **WHEN** classification is triggered
- **THEN** rules are evaluated first
- **AND** if no match or disambiguation required, AI disambiguation is queued
- **AND** final category is written to transaction_categories

#### Scenario: Batch classification
- **GIVEN** multiple uncategorized transactions exist
- **WHEN** batch classification is triggered
- **THEN** rules are evaluated for all transactions
- **AND** AI disambiguation is queued for eligible transactions
- **AND** processing continues without blocking on individual failures

#### Scenario: Classification idempotency
- **GIVEN** a transaction has already been classified
- **WHEN** classification is triggered again
- **THEN** existing classification is preserved unless force flag is set
- **AND** re-classification with force flag updates the category and evidence
