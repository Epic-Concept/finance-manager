# local-database Specification

## Purpose
TBD - created by archiving change add-local-database. Update Purpose after archive.
## Requirements
### Requirement: Local Database Container
The system SHALL provide a Docker-based SQL Server 2022 instance for local development.

#### Scenario: Starting local database
- **GIVEN** Docker is installed and running
- **WHEN** the developer runs `docker-compose up db`
- **THEN** a SQL Server 2022 container starts
- **AND** the database is accessible on port 1433
- **AND** the container reports healthy within 60 seconds

#### Scenario: Database persistence
- **GIVEN** the local database container is running
- **WHEN** data is written to the database
- **AND** the container is stopped and restarted
- **THEN** the data persists between restarts

### Requirement: Docker Compose Orchestration
The system SHALL provide docker-compose configuration for running all services locally.

#### Scenario: Starting all services
- **GIVEN** Docker is installed and running
- **WHEN** the developer runs `docker-compose up`
- **THEN** the database, API, and web services start
- **AND** the API waits for the database to be healthy before starting
- **AND** all services are accessible on their configured ports

#### Scenario: Service networking
- **GIVEN** all services are running via docker-compose
- **WHEN** the API connects to the database
- **THEN** the connection uses the internal Docker network
- **AND** the connection string references the service name `db`

### Requirement: Database Migrations
The system SHALL use Alembic for database schema migrations.

#### Scenario: Running migrations
- **GIVEN** the database is running
- **WHEN** the developer runs `alembic upgrade head`
- **THEN** all pending migrations are applied
- **AND** the migration history is recorded in `alembic_version` table

#### Scenario: Creating new migrations
- **GIVEN** the database module is configured
- **WHEN** the developer runs `alembic revision --autogenerate -m "description"`
- **THEN** a new migration file is created in `alembic/versions/`
- **AND** the migration captures model changes

#### Scenario: Migration rollback
- **GIVEN** migrations have been applied
- **WHEN** the developer runs `alembic downgrade -1`
- **THEN** the most recent migration is reverted
- **AND** the schema returns to the previous state

### Requirement: Database Health Check
The API health endpoint SHALL verify database connectivity.

#### Scenario: Health check with database
- **GIVEN** the API is running
- **AND** the database is healthy
- **WHEN** a GET request is made to `/health`
- **THEN** the response includes database status
- **AND** the status indicates the database is connected

#### Scenario: Health check without database
- **GIVEN** the API is running
- **AND** the database is unavailable
- **WHEN** a GET request is made to `/health`
- **THEN** the response indicates degraded health
- **AND** the database status shows disconnected

### Requirement: CI Database Integration
The CI pipeline SHALL validate database migrations.

#### Scenario: CI migration validation
- **WHEN** the CI pipeline runs
- **THEN** a SQL Server container is started as a service
- **AND** Alembic migrations are applied
- **AND** the pipeline fails if migrations fail

#### Scenario: CI database tests
- **WHEN** the CI pipeline runs backend tests
- **THEN** tests have access to a running database
- **AND** tests can verify database operations

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

