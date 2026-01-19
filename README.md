# Finance Manager

A personal finance management application built with FastAPI backend and React frontend.

## Project Structure

```
finance_manager/
├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # React/TypeScript frontend
├── infra/            # Terraform infrastructure (Azure)
├── docs/             # Documentation
│   ├── architecture/ # Architecture Decision Records
│   ├── api/          # API documentation
│   └── guides/       # Developer guides
└── .github/workflows # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (optional)
- Terraform 1.5+ (for infrastructure)

### Backend (API)

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn finance_api.main:app --reload
```

### Frontend (Web)

```bash
cd apps/web
npm install
npm run dev
```

### Using Make

```bash
# Install all dependencies
make install

# Run all tests
make test

# Run linting
make lint

# Build Docker images
make docker-build

# Run the full application
make run
```

## Development

### Code Style

- **Python**: Black, Ruff, MyPy
- **TypeScript**: ESLint, Prettier

### Testing

- **Backend**: pytest with coverage
- **Frontend**: Vitest with React Testing Library

## Deployment

Docker images are automatically built and pushed to GitHub Container Registry on merges to `main`.

- API: `ghcr.io/<owner>/finance-manager-api`
- Web: `ghcr.io/<owner>/finance-manager-web`

## Documentation

- [Architecture Decisions](docs/architecture/)
- [API Documentation](docs/api/)
- [Developer Guides](docs/guides/)

## License

MIT
