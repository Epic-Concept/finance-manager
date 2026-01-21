# Tasks: Bootstrap Monorepo Structure and CI/CD Pipeline

## 1. Root Configuration
- [ ] 1.1 Create root `.gitignore` with Python, Node, Terraform patterns
- [ ] 1.2 Create root `README.md` with project overview and getting started
- [ ] 1.3 Create `Makefile` with common commands (install, test, lint, build)

## 2. Backend Setup (apps/api)
- [ ] 2.1 Create `apps/api/` directory structure
- [ ] 2.2 Create `pyproject.toml` with dependencies (fastapi, uvicorn, pytest, black, ruff)
- [ ] 2.3 Create minimal `src/finance_api/main.py` with health check endpoint
- [ ] 2.4 Create placeholder directories (routers/, services/, repositories/, models/, core/)
- [ ] 2.5 Create `tests/test_main.py` with health check test
- [ ] 2.6 Create multi-stage `Dockerfile`
- [ ] 2.7 Create `apps/api/README.md` with local development instructions

## 3. Frontend Setup (apps/web)
- [ ] 3.1 Create `apps/web/` directory structure (use Vite + React template)
- [ ] 3.2 Configure `package.json` with React 18, TypeScript, Vite
- [ ] 3.3 Configure `tsconfig.json` with strict mode
- [ ] 3.4 Configure ESLint and Prettier
- [ ] 3.5 Create minimal `App.tsx` with "Finance Manager" heading
- [ ] 3.6 Create placeholder directories (components/, hooks/, pages/, services/, types/)
- [ ] 3.7 Create basic test with Jest/Vitest
- [ ] 3.8 Create multi-stage `Dockerfile` (build + nginx)
- [ ] 3.9 Create `apps/web/README.md` with local development instructions

## 4. Infrastructure Setup (infra/)
- [ ] 4.1 Create `infra/` directory structure
- [ ] 4.2 Create `main.tf` with Azure provider configuration (validate only, no plan/apply)
- [ ] 4.3 Create `variables.tf` with common variables
- [ ] 4.4 Create placeholder module structure (modules/database/, modules/container-app/)
- [ ] 4.5 Create `infra/README.md` with usage instructions

> **Note:** IaC is validation-only at this stage. Do NOT run `terraform plan` or `terraform apply`.

## 5. Documentation Setup (docs/)
- [ ] 5.1 Create `docs/` directory structure
- [ ] 5.2 Create `docs/architecture/` for architecture decision records
- [ ] 5.3 Create `docs/api/` for API documentation
- [ ] 5.4 Create `docs/guides/` for developer guides
- [ ] 5.5 Create `docs/README.md` with documentation overview

## 6. CI/CD Pipeline
- [ ] 6.1 Create `.github/workflows/ci.yml` with parallel jobs:
  - API: lint (ruff, black --check), test (pytest)
  - Web: lint (eslint), format check (prettier), test (jest/vitest)
  - Infra: terraform fmt -check, terraform validate (no plan/apply)
- [ ] 6.2 Create `.github/workflows/publish.yml` for Docker image publishing:
  - Trigger on push to main
  - Build and push API image to ghcr.io
  - Build and push Web image to ghcr.io
  - Tag with `latest` and commit SHA

## 7. Validation
- [ ] 7.1 Verify all directories created correctly
- [ ] 7.2 Run backend tests locally
- [ ] 7.3 Run frontend tests locally
- [ ] 7.4 Run `terraform fmt -check` and `terraform validate` (no plan/apply)
- [ ] 7.5 Verify CI workflow passes on test push
- [ ] 7.6 Verify Docker images build locally
