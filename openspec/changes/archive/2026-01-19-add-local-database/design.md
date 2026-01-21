# Design: Add Local Development Database

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    docker-compose                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Web       │  │    API      │  │   SQL Server 2022   │  │
│  │  (nginx)    │  │  (FastAPI)  │  │   (mssql:2022)      │  │
│  │  port:5173  │  │  port:8000  │  │   port:1433         │  │
│  └─────────────┘  └──────┬──────┘  └──────────┬──────────┘  │
│                          │                     │             │
│                          └─────────────────────┘             │
│                            SQLAlchemy + pyodbc               │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. SQL Server 2022 over PostgreSQL
**Decision:** Use SQL Server 2022 to match the production Azure SQL target.

**Rationale:**
- Azure SQL is SQL Server-based; local dev should match production
- Avoids SQL dialect differences between dev and prod
- Microsoft provides official Docker images
- pyodbc is mature and well-supported

**Trade-offs:**
- SQL Server container requires more resources (~2GB RAM)
- macOS requires Docker Desktop or Colima with Rosetta (ARM translation)

### 2. Alembic for Migrations
**Decision:** Use Alembic as the migration framework.

**Rationale:**
- Native integration with SQLAlchemy
- Supports autogenerate from model changes
- Version-controlled migration history
- Industry standard for Python projects
- Supports both upgrade and downgrade paths

**Alternatives Considered:**
- Plain SQL scripts: More explicit but harder to manage, no autogenerate
- Django migrations: Would require Django, not applicable to FastAPI

### 3. SQLAlchemy 2.0 ORM
**Decision:** Use SQLAlchemy 2.0 with the new typing-focused API.

**Rationale:**
- Modern async support aligns with FastAPI
- Strong typing with `Mapped[]` annotations
- Well-documented, widely used
- Declarative model definitions

### 4. Connection String Management
**Decision:** Use environment variables with pydantic-settings.

**Configuration:**
```python
# Environment variables
DATABASE_URL=mssql+pyodbc://sa:Password123!@localhost:1433/finance_manager?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

**Rationale:**
- Follows 12-factor app principles
- Different values for local/CI/production
- pydantic-settings validates and types the config

### 5. Docker Compose Service Dependencies
**Decision:** Use `depends_on` with health checks for startup ordering.

```yaml
services:
  db:
    healthcheck:
      test: /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$$SA_PASSWORD" -Q "SELECT 1" -C
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 30s

  api:
    depends_on:
      db:
        condition: service_healthy
```

**Rationale:**
- Ensures database is ready before API starts
- Prevents connection errors during startup
- Health check validates actual SQL connectivity

## Database Module Structure

```
apps/api/
├── alembic/
│   ├── versions/           # Migration files
│   ├── env.py              # Alembic environment config
│   └── script.py.mako      # Migration template
├── alembic.ini             # Alembic configuration
└── src/finance_api/
    └── db/
        ├── __init__.py     # Exports engine, SessionLocal, Base
        ├── engine.py       # SQLAlchemy engine configuration
        ├── session.py      # Session factory and dependency
        └── base.py         # Declarative base class
```

## CI/CD Integration

### GitHub Actions Service Container
```yaml
services:
  mssql:
    image: mcr.microsoft.com/mssql/server:2022-latest
    env:
      ACCEPT_EULA: Y
      SA_PASSWORD: TestPassword123!
    ports:
      - 1433:1433
    options: >-
      --health-cmd "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P TestPassword123! -Q 'SELECT 1' -C"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 10
```

### Migration Validation Step
```yaml
- name: Run migrations
  run: |
    cd apps/api
    alembic upgrade head
  env:
    DATABASE_URL: mssql+pyodbc://sa:TestPassword123!@localhost:1433/master?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## Security Considerations

1. **Local Development Password:** Use a simple password (`Password123!`) for local dev only
2. **CI Password:** Use a test password, not stored in secrets
3. **Production:** Will use Azure SQL with managed identity (future change)
4. **Connection String:** Never commit real credentials; use environment variables
5. **TrustServerCertificate:** Only enabled for local dev, not for production
