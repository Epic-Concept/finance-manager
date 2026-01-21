# database-schema Specification Delta

## ADDED Requirements

### Requirement: Email Account Storage
The system MUST store email account configurations for purchase receipt retrieval.

#### Scenario: Email accounts table structure
- **GIVEN** the finance schema exists
- **WHEN** the email_accounts table is created
- **THEN** it contains columns for id, email_address, display_name, provider, imap_server, imap_port, credential_reference, is_active, priority, created_at, updated_at
- **AND** email_address has a unique constraint
- **AND** provider accepts values: gmail, outlook, imap_generic
- **AND** imap_port defaults to 993
- **AND** is_active defaults to true
- **AND** priority defaults to 0

#### Scenario: Multiple email accounts per user
- **GIVEN** the email_accounts table exists
- **WHEN** a user configures multiple email accounts
- **THEN** each account is stored with a unique email_address
- **AND** accounts are searched in priority order (lower priority first)

### Requirement: Classification Rules Storage
The system MUST store classification rules for the rules engine.

#### Scenario: Classification rules table structure
- **GIVEN** the finance schema exists
- **WHEN** the classification_rules table is created
- **THEN** it contains columns for id, name, rule_expression, category_id, priority, requires_disambiguation, is_active, created_at, updated_at
- **AND** category_id references categories(id)
- **AND** priority defaults to 0
- **AND** requires_disambiguation defaults to false
- **AND** is_active defaults to true
- **AND** an index exists on (is_active, priority)

#### Scenario: Rule evaluation order
- **GIVEN** multiple active classification rules exist
- **WHEN** evaluating rules for a transaction
- **THEN** rules are evaluated in ascending priority order
- **AND** the first matching rule is applied

### Requirement: Category Evidence Storage
The system MUST store classification evidence for audit and future transaction splitting.

#### Scenario: Category evidence table structure
- **GIVEN** the finance schema exists
- **WHEN** the category_evidence table is created
- **THEN** it contains columns for id, transaction_id, item_description, item_price, item_currency, item_quantity, category_id, evidence_type, email_account_id, email_message_id, email_datetime, evidence_summary, confidence_score, model_used, raw_extraction, created_at, updated_at
- **AND** transaction_id references transactions(id)
- **AND** category_id references categories(id)
- **AND** email_account_id optionally references email_accounts(id)
- **AND** item_price uses DECIMAL(19,4) for precision
- **AND** confidence_score uses DECIMAL(5,4) for precision
- **AND** item_quantity defaults to 1
- **AND** item_currency defaults to 'GBP'
- **AND** indexes exist on transaction_id, category_id, and (email_account_id, email_message_id)

#### Scenario: Multi-item purchase evidence
- **GIVEN** a transaction for a multi-item online purchase exists
- **WHEN** classification evidence is stored
- **THEN** one row is created per item in category_evidence
- **AND** each row links to the same transaction_id
- **AND** shipping costs are stored as a separate row with item_description 'Shipping'

#### Scenario: Evidence provenance
- **GIVEN** a transaction is classified via email receipt
- **WHEN** evidence is stored
- **THEN** evidence_type is set to 'email'
- **AND** email_account_id references the source email account
- **AND** email_message_id stores the email Message-ID header
- **AND** email_datetime stores when the email was sent
- **AND** evidence_summary contains a human-readable description
