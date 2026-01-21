# cicd-pipeline Specification

## Purpose
TBD - created by archiving change bootstrap-monorepo. Update Purpose after archive.
## Requirements
### Requirement: Continuous Integration
The CI pipeline SHALL validate all components on every code change.

#### Scenario: CI triggers on push
- **WHEN** code is pushed to any branch
- **THEN** the CI workflow runs validation for all affected components

#### Scenario: CI triggers on pull request
- **WHEN** a pull request is opened or updated against main
- **THEN** the CI workflow runs validation for all components

### Requirement: Backend Validation
The CI pipeline SHALL validate backend code quality and correctness.

#### Scenario: Backend linting
- **WHEN** the CI pipeline runs backend validation
- **THEN** Ruff linting checks are executed
- **AND** Black formatting checks are executed
- **AND** the job fails if any check fails

#### Scenario: Backend testing
- **WHEN** the CI pipeline runs backend validation
- **THEN** pytest runs all tests in `apps/api/tests/`
- **AND** the job fails if any test fails

### Requirement: Frontend Validation
The CI pipeline SHALL validate frontend code quality and correctness.

#### Scenario: Frontend linting
- **WHEN** the CI pipeline runs frontend validation
- **THEN** ESLint checks are executed
- **AND** Prettier formatting checks are executed
- **AND** the job fails if any check fails

#### Scenario: Frontend testing
- **WHEN** the CI pipeline runs frontend validation
- **THEN** the test runner executes all tests in `apps/web/`
- **AND** the job fails if any test fails

### Requirement: Infrastructure Validation
The CI pipeline SHALL validate Terraform code.

#### Scenario: Terraform validation
- **WHEN** the CI pipeline runs infrastructure validation
- **THEN** `terraform fmt -check` verifies formatting
- **AND** `terraform validate` verifies configuration syntax
- **AND** the job fails if any check fails

### Requirement: Docker Image Publishing
The CI/CD pipeline SHALL publish Docker images to GitHub Container Registry on successful main branch builds.

#### Scenario: API image publishing
- **WHEN** code is pushed to the main branch
- **AND** all CI checks pass
- **THEN** the API Docker image is built
- **AND** the image is pushed to `ghcr.io/<owner>/finance-api:latest`
- **AND** the image is tagged with the commit SHA

#### Scenario: Web image publishing
- **WHEN** code is pushed to the main branch
- **AND** all CI checks pass
- **THEN** the Web Docker image is built
- **AND** the image is pushed to `ghcr.io/<owner>/finance-web:latest`
- **AND** the image is tagged with the commit SHA

### Requirement: Parallel Job Execution
The CI pipeline SHALL run independent jobs in parallel to minimize build time.

#### Scenario: Parallel validation jobs
- **WHEN** the CI workflow is triggered
- **THEN** backend, frontend, and infrastructure validation jobs run in parallel

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

