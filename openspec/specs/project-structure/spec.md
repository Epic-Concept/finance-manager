# project-structure Specification

## Purpose
TBD - created by archiving change bootstrap-monorepo. Update Purpose after archive.
## Requirements
### Requirement: Monorepo Directory Organization
The project SHALL be organized as a monorepo with distinct directories for each component type.

#### Scenario: Application components location
- **WHEN** a developer looks for application code
- **THEN** backend API code is located in `apps/api/`
- **AND** frontend web code is located in `apps/web/`

#### Scenario: Infrastructure code location
- **WHEN** a developer looks for infrastructure definitions
- **THEN** Terraform code is located in `infra/`

#### Scenario: Documentation location
- **WHEN** a developer looks for project documentation
- **THEN** documentation is located in `docs/`

### Requirement: Backend Application Structure
The backend application SHALL follow a layered architecture with clear separation of concerns.

#### Scenario: API layer organization
- **WHEN** a developer examines the backend structure
- **THEN** the code is organized under `apps/api/src/finance_api/`
- **AND** route handlers are in `routers/`
- **AND** business logic is in `services/`
- **AND** data access is in `repositories/`
- **AND** data models are in `models/`

#### Scenario: Backend test location
- **WHEN** a developer writes or runs backend tests
- **THEN** tests are located in `apps/api/tests/`

### Requirement: Frontend Application Structure
The frontend application SHALL follow a component-based architecture.

#### Scenario: Frontend organization
- **WHEN** a developer examines the frontend structure
- **THEN** the code is organized under `apps/web/src/`
- **AND** reusable components are in `components/`
- **AND** custom hooks are in `hooks/`
- **AND** page components are in `pages/`
- **AND** API client code is in `services/`

### Requirement: Infrastructure Code Structure
The infrastructure code SHALL use Terraform modules for reusability.

#### Scenario: Infrastructure organization
- **WHEN** a developer examines infrastructure code
- **THEN** reusable modules are in `infra/modules/`
- **AND** environment-specific configurations are in `infra/environments/`

### Requirement: Development Configuration
Each component SHALL have self-contained configuration for local development.

#### Scenario: Backend configuration
- **WHEN** a developer sets up the backend locally
- **THEN** `apps/api/pyproject.toml` contains all Python dependencies
- **AND** `apps/api/README.md` documents local setup steps

#### Scenario: Frontend configuration
- **WHEN** a developer sets up the frontend locally
- **THEN** `apps/web/package.json` contains all Node.js dependencies
- **AND** `apps/web/README.md` documents local setup steps

### Requirement: Documentation Structure
The project documentation SHALL be organized by purpose.

#### Scenario: Documentation organization
- **WHEN** a developer examines the documentation structure
- **THEN** architecture decision records are in `docs/architecture/`
- **AND** API documentation is in `docs/api/`
- **AND** developer guides are in `docs/guides/`

