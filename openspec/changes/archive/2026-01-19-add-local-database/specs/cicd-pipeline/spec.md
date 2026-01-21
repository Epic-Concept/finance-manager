# cicd-pipeline Specification Delta

## ADDED Requirements

### Requirement: Database Service in CI
The CI pipeline SHALL include a SQL Server service container for database-dependent tests.

#### Scenario: Database service startup
- **WHEN** the CI workflow starts backend validation
- **THEN** a SQL Server 2022 container is started as a service
- **AND** the service is healthy before tests begin
- **AND** the ODBC driver is installed in the runner

### Requirement: Migration Validation
The CI pipeline SHALL validate that all migrations apply cleanly.

#### Scenario: Migration check
- **WHEN** the CI pipeline runs backend validation
- **THEN** `alembic upgrade head` is executed
- **AND** the job fails if any migration fails to apply
