## ADDED Requirements

### Requirement: Incremental pull-sync from the upstream source

The system SHALL pull transactions from the upstream **Azure SQL** database (read-only, authenticated with an Entra service principal over SSL) into the gb10 store incrementally, using a persisted `synced_at` cursor so each run fetches only records newer than the last successful sync. The sync SHALL be pull-based (gb10 initiates); the upstream SHALL NOT require inbound access to gb10.

#### Scenario: Only new records are fetched

- **WHEN** a sync runs with a stored cursor
- **THEN** it requests only source rows whose `synced_at` is greater than the cursor and advances the cursor to the newest synced record on success

#### Scenario: First sync has no cursor

- **WHEN** a sync runs with no stored cursor
- **THEN** it fetches all available source rows and establishes the cursor

### Requirement: Idempotent upsert

The system SHALL key incoming transactions by their source `transaction_id` (stored as `external_id`) and SHALL NOT create duplicate transactions when the same source row is seen again.

#### Scenario: Re-syncing an already-imported transaction

- **WHEN** a source row whose `transaction_id` already exists locally is synced again
- **THEN** no duplicate transaction is created

### Requirement: Normalization to the canonical model

The system SHALL map source columns to the canonical `Transaction` (transaction_id→external_id; transaction_date, amount, currency, account_name, description, merchant_name) and persist amounts as exact decimals.

#### Scenario: Source row becomes a canonical transaction

- **WHEN** a source row is synced
- **THEN** a `Transaction` is stored with the mapped fields and an exact-decimal amount

### Requirement: Scheduled nightly sync

The system SHALL provide a runnable sync entrypoint suitable for scheduling on gb10 (cron / systemd timer) after the upstream evening refresh. A sync failure SHALL leave the cursor unchanged so the next run retries the same window.

#### Scenario: Failed sync does not advance the cursor

- **WHEN** a sync fails partway
- **THEN** the cursor is not advanced and the next run re-attempts the unsynced records
