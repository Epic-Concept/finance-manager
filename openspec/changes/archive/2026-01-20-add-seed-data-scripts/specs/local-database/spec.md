## ADDED Requirements

### Requirement: Seed Data Scripts
The system SHALL provide scripts to populate the local database with development data from CSV files.

#### Scenario: Loading bank transactions
- **GIVEN** the local database is running with migrations applied
- **AND** a `data/bank_transactions.csv` file exists
- **WHEN** the developer runs the seed data script for transactions
- **THEN** records are inserted into the `finance.transactions` table
- **AND** the CSV columns are mapped to the appropriate database columns

#### Scenario: Loading purchases
- **GIVEN** the local database is running with migrations applied
- **AND** a `data/purchases.csv` file exists
- **WHEN** the developer runs the seed data script for purchases
- **THEN** records are inserted into the `finance.online_purchases` table
- **AND** the CSV columns are mapped to the appropriate database columns

#### Scenario: Clearing existing data
- **GIVEN** the local database contains seed data
- **WHEN** the developer runs the seed script with the `--clear` flag
- **THEN** existing records are deleted before new data is inserted
- **AND** foreign key constraints are respected during deletion

#### Scenario: Idempotent seeding
- **GIVEN** seed data has already been loaded
- **WHEN** the developer runs the seed script again without `--clear`
- **THEN** duplicate records are skipped based on unique identifiers
- **AND** new records are inserted

### Requirement: Data Folder Exclusion
The `data/` folder SHALL be excluded from version control to protect sensitive financial data.

#### Scenario: Gitignore includes data folder
- **GIVEN** the repository `.gitignore` file
- **WHEN** a developer adds files to `data/`
- **THEN** the files are not tracked by git
- **AND** `git status` does not show the data files as untracked

### Requirement: Makefile Integration
The seed data operations SHALL be accessible via Makefile targets.

#### Scenario: Make seed-data target
- **GIVEN** the local database is running
- **AND** CSV files exist in `data/`
- **WHEN** the developer runs `make seed-data`
- **THEN** all CSV data is loaded into the database

#### Scenario: Make seed-data-clear target
- **GIVEN** the local database contains existing data
- **WHEN** the developer runs `make seed-data-clear`
- **THEN** existing seed data is cleared
- **AND** fresh data is loaded from CSV files
