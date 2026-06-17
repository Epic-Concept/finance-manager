## ADDED Requirements

### Requirement: PostgreSQL as the persistence platform

The system SHALL use PostgreSQL as its primary data store, accessed via a Postgres SQLAlchemy driver (`postgresql+psycopg`). The system SHALL NOT depend on Microsoft SQL Server or the ODBC/`pyodbc` driver.

#### Scenario: Application connects to Postgres

- **WHEN** the API starts with a `postgresql+psycopg` connection URL pointing at PostgreSQL on `gb10.local`
- **THEN** it establishes a database connection and serves requests without any SQL Server or ODBC dependency

#### Scenario: No SQL Server driver remains

- **WHEN** the project dependencies are installed
- **THEN** `pyodbc` is absent and a Postgres driver is present

### Requirement: Dialect-portable migrations on the finance schema

All Alembic migrations SHALL run successfully on PostgreSQL and SHALL create the `finance` schema using portable Postgres SQL rather than T-SQL. The full migration chain SHALL upgrade a fresh Postgres database from base to head without error.

#### Scenario: Schema creation uses Postgres SQL

- **WHEN** the schema-creation migration runs on PostgreSQL
- **THEN** it creates the `finance` schema using `CREATE SCHEMA IF NOT EXISTS` semantics and contains no `sys.schemas`/`EXEC` T-SQL

#### Scenario: Full migration chain applies on a fresh database

- **WHEN** `alembic upgrade head` runs against an empty PostgreSQL database
- **THEN** all migrations apply successfully and produce the expected `finance`-schema tables

### Requirement: Data model parity on Postgres

The existing domain tables and their columns, constraints, and indexes SHALL be reproduced on PostgreSQL, preserving exact decimal handling for monetary amounts.

#### Scenario: Monetary amounts keep exact precision

- **WHEN** a transaction amount is written and read back on PostgreSQL
- **THEN** the value is stored and returned as an exact decimal with no floating-point rounding

#### Scenario: Existing repositories operate unchanged

- **WHEN** the existing repository and integration tests run against PostgreSQL
- **THEN** they pass without changes to application-level query behavior
