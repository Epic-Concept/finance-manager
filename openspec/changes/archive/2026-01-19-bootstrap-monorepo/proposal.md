# Change: Bootstrap Monorepo Structure and CI/CD Pipeline

## Why
The project needs a foundational directory structure and automated build pipeline before any features can be developed. A well-organized monorepo enables parallel development across backend, frontend, and infrastructure components while ensuring consistent builds and artifact publishing.

## What Changes
- Establish monorepo directory structure with three components:
  - `apps/api/` - Python FastAPI backend
  - `apps/web/` - React TypeScript frontend
  - `infra/` - Infrastructure-as-Code (Terraform for Azure)
- Create GitHub Actions CI/CD pipeline that:
  - Builds and tests all components on every push/PR
  - Publishes Docker images to GitHub Container Registry (ghcr.io)
  - Runs linting and type checking
- Add root-level configuration for workspace management
- Create skeleton application code with minimal "hello world" implementations

## Impact
- Affected specs: `project-structure`, `cicd-pipeline` (new capabilities)
- Affected code: All directories (new project scaffold)
- **BREAKING**: N/A (greenfield project)

## Success Criteria
- All three component directories exist with basic structure
- CI pipeline runs successfully on push to any branch
- Docker images are built and pushed to ghcr.io on main branch
- Each component can be developed and tested independently
