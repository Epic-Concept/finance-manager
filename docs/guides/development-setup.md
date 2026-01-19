# Development Setup

This guide walks through setting up a local development environment for the Finance Manager application.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (required for database and full stack development)
- ODBC Driver 18 for SQL Server (for local API development without Docker)

### Installing ODBC Driver (macOS)

```bash
brew install microsoft/mssql-release/msodbcsql18
```

### Installing ODBC Driver (Ubuntu/Debian)

```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
```

## Quick Start (Docker Compose)

The fastest way to get started is using Docker Compose:

```bash
# Start all services (database, API, web)
docker-compose up

# Or start in background
docker-compose up -d
```

This starts:
- SQL Server 2022 on port 1433
- API on http://localhost:8000
- Web on http://localhost:80

## Database Setup

### Starting the Database

```bash
# Start only the database
make db-up

# Or using docker-compose directly
docker-compose up -d db
```

The database will be available at `localhost:1433` with:
- Username: `sa`
- Password: `Password123!` (default, change via `DB_PASSWORD` env var)

### Running Migrations

```bash
# Apply all migrations
make db-migrate

# Or manually
cd apps/api
alembic upgrade head
```

### Creating New Migrations

```bash
cd apps/api
alembic revision --autogenerate -m "description of change"
```

### Resetting the Database

```bash
# Destroys all data and recreates the database
make db-reset
```

## Backend Setup (Without Docker)

1. Start the database:
   ```bash
   make db-up
   ```

2. Navigate to the API directory:
   ```bash
   cd apps/api
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

5. Set up environment:
   ```bash
   cp ../../.env.example .env
   ```

6. Run migrations:
   ```bash
   alembic upgrade head
   ```

7. Run tests:
   ```bash
   pytest
   ```

8. Start the development server:
   ```bash
   uvicorn finance_api.main:app --reload
   ```

The API will be available at http://localhost:8000.

## Frontend Setup

1. Navigate to the web directory:
   ```bash
   cd apps/web
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run tests:
   ```bash
   npm test
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

The web app will be available at http://localhost:5173.

## Using Make

From the repository root:

```bash
# Install all dependencies
make install

# Run all tests
make test

# Run all linters
make lint

# Format code
make format

# Database commands
make db-up        # Start database
make db-down      # Stop database
make db-migrate   # Run migrations
make db-reset     # Reset database

# Start all services
make run
```

## Environment Variables

Copy `.env.example` to `.env` and customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQL Server connection string | See .env.example |
| `DB_PASSWORD` | Database SA password | `Password123!` |
| `DB_PORT` | Database port | `1433` |
| `API_PORT` | API port | `8000` |
| `WEB_PORT` | Web port | `80` |

## IDE Configuration

### VS Code

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Terraform
- Docker

### PyCharm / WebStorm

1. Mark `apps/api/src` as Python source root
2. Mark `apps/web/src` as JavaScript source root
3. Configure Python interpreter to use the virtual environment

## Troubleshooting

### Database connection issues

1. Ensure Docker is running
2. Check the database is healthy: `docker-compose ps`
3. Verify ODBC driver is installed: `odbcinst -q -d`
4. Check connection string in `.env`

### API not starting

1. Ensure virtual environment is activated
2. Check that all dependencies are installed: `pip install -e ".[dev]"`
3. Verify Python version: `python --version` (should be 3.11+)
4. Ensure database is running and migrations are applied

### Frontend not connecting to API

1. Ensure the API is running on port 8000
2. Check the proxy configuration in `vite.config.ts`
3. Look for CORS errors in the browser console

### SQL Server container won't start

SQL Server requires at least 2GB of RAM. On Docker Desktop:
1. Go to Settings → Resources
2. Increase memory to at least 4GB
3. Restart Docker Desktop
