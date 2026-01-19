# ADR-001: Monorepo Structure

## Status
Accepted

## Context
The Finance Manager application consists of multiple components:
- FastAPI backend (API)
- React/TypeScript frontend (Web)
- Terraform infrastructure (IaC)
- Documentation

We need to decide how to organize these components for development and deployment.

## Decision
We will use a monorepo structure with the following layout:

```
finance_manager/
├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # React frontend
├── infra/            # Terraform infrastructure
├── docs/             # Documentation
└── .github/workflows # CI/CD pipelines
```

### Key Design Choices

1. **Separate `apps/` directory** - Application code is isolated from infrastructure and documentation
2. **Independent packages** - Each app has its own package configuration (`pyproject.toml`, `package.json`)
3. **Shared CI/CD** - Single GitHub Actions workflow handles all components
4. **Docker images per app** - Each application has its own Dockerfile for independent deployment

## Consequences

### Positive
- Single repository to clone and manage
- Easier cross-cutting changes (API and frontend together)
- Unified CI/CD pipeline
- Consistent tooling across components

### Negative
- Larger repository size over time
- CI runs for all components on any change (mitigated by path filters)
- Need for careful dependency management

### Neutral
- Requires discipline in maintaining clear boundaries between components
- Team members need familiarity with all technologies (Python, TypeScript, Terraform)
