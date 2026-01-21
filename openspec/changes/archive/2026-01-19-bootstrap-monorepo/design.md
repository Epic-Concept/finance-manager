# Design: Monorepo Structure and CI/CD Pipeline

## Context
This is the initial project setup for a personal finance management application. The architecture must support:
- Python 3.11+ FastAPI backend
- React/TypeScript frontend
- Azure SQL database (cloud-hosted)
- Infrastructure-as-Code for Azure resources
- TDD approach with high test coverage requirements

## Goals
- Establish clear separation between components while enabling code sharing
- Provide consistent developer experience across all components
- Automate build, test, and artifact publishing
- Support independent component development and deployment

## Non-Goals
- Automated deployment to Azure (handled separately)
- Multi-environment configuration (dev/staging/prod)
- Shared component libraries between frontend/backend (future enhancement)

## Decisions

### 1. Directory Structure
**Decision:** Use flat component structure under `apps/` for applications and `infra/` for IaC.

```
finance_manager/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── src/
│   │   │   └── finance_api/    # Python package
│   │   │       ├── __init__.py
│   │   │       ├── main.py     # FastAPI app entry
│   │   │       ├── routers/    # API endpoints
│   │   │       ├── services/   # Business logic
│   │   │       ├── repositories/ # Data access
│   │   │       └── models/     # Pydantic models
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── web/                    # React frontend
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── pages/
│       │   ├── services/       # API client
│       │   └── App.tsx
│       ├── tests/
│       ├── Dockerfile
│       ├── package.json
│       ├── tsconfig.json
│       └── README.md
│
├── infra/                      # Infrastructure-as-Code
│   ├── modules/                # Reusable Terraform modules
│   │   ├── database/
│   │   └── container-app/
│   ├── environments/           # Environment-specific configs
│   │   └── production/
│   ├── main.tf
│   ├── variables.tf
│   └── README.md
│
├── docs/                       # Documentation
│   ├── architecture/           # Architecture decision records
│   ├── api/                    # API documentation
│   └── guides/                 # Developer guides
│
├── .github/
│   └── workflows/
│       ├── ci.yml              # Build and test
│       └── publish.yml         # Docker image publishing
│
├── openspec/                   # Specifications (existing)
├── .gitignore
├── README.md
└── Makefile                    # Common commands
```

**Alternatives considered:**
- Nx/Turborepo workspace: Adds complexity not needed initially; can migrate later
- Separate repositories: Increases coordination overhead for small team

### 2. Package Management
**Decision:** Use native tools per ecosystem without monorepo orchestration.

- Python: `pyproject.toml` with `pip` (consider `uv` for speed)
- Node.js: `package.json` with `npm`
- Terraform: Standard Terraform CLI

**Rationale:** Simplest approach for initial setup; no learning curve for specialized tools.

### 3. CI/CD Pipeline Structure
**Decision:** Two separate workflows - CI for testing, Publish for artifacts.

**CI Workflow (ci.yml):**
- Triggers: push to any branch, pull requests to main
- Jobs (parallel where possible):
  - `api-lint-test`: Ruff linting, Black formatting check, pytest
  - `web-lint-test`: ESLint, Prettier check, Jest
  - `infra-validate`: Terraform fmt, validate

**Publish Workflow (publish.yml):**
- Triggers: push to main branch only
- Jobs:
  - `build-api`: Build and push API Docker image to ghcr.io
  - `build-web`: Build and push Web Docker image to ghcr.io

**Rationale:** Separating concerns allows CI to run fast on PRs while publish only happens on main.

### 4. Docker Image Strategy
**Decision:** Multi-stage builds with minimal final images.

- API: `python:3.11-slim` base
- Web: nginx with static build output

**Image tagging:**
- `ghcr.io/<owner>/finance-api:latest` (main branch)
- `ghcr.io/<owner>/finance-api:<sha>` (specific commit)
- `ghcr.io/<owner>/finance-web:latest`
- `ghcr.io/<owner>/finance-web:<sha>`

### 5. Python Backend Structure
**Decision:** Follow repository pattern as specified in project.md.

```
src/finance_api/
├── main.py           # FastAPI app, middleware, exception handlers
├── routers/          # Route definitions, request/response handling
├── services/         # Business logic, orchestration
├── repositories/     # Data access, database queries
├── models/           # Pydantic models (request/response/domain)
└── core/             # Config, dependencies, utilities
```

### 6. Frontend Structure
**Decision:** Standard React structure with feature-based organization.

```
src/
├── components/       # Reusable UI components
├── hooks/           # Custom React hooks
├── pages/           # Page-level components
├── services/        # API client, external integrations
├── types/           # TypeScript type definitions
└── utils/           # Helper functions
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| No workspace orchestration may slow builds | Components are small; parallel CI jobs compensate |
| Terraform state management not addressed | Defer to deployment proposal; use local state initially |
| No shared types between frontend/backend | Generate OpenAPI client in future enhancement |

## Open Questions
1. Should we use `uv` instead of `pip` for faster Python dependency management?
2. Should Terraform state be stored in Azure Storage from the start?

## Migration Plan
N/A - Greenfield project
