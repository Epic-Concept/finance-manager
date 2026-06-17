# self-hosted-deployment Specification

## Purpose

Defines the self-hosted, single-host deployment model for the finance system on `gb10.local`, including co-location of services, data residency, and backup/restore.

## Requirements

### Requirement: Single-host co-located deployment on gb10.local

The application, PostgreSQL, and the local LLM SHALL run co-located on `gb10.local`. The deployment SHALL function without any required cloud service.

#### Scenario: Stack runs on one host

- **WHEN** the deployment is brought up on `gb10.local`
- **THEN** the API, PostgreSQL, and the local LLM are all reachable on that host and the application operates without contacting a cloud service

#### Scenario: Local LLM is reachable from the app

- **WHEN** the classification workflow needs the local model
- **THEN** it reaches the LLM on `gb10.local` over the local network

### Requirement: Data stays on the host

Financial data and raw mailbox content SHALL remain on `gb10.local` and SHALL NOT be transmitted to any third-party or cloud service as part of normal operation.

#### Scenario: No external egress of sensitive data

- **WHEN** the system stores transactions or processes mailbox content
- **THEN** that data is written to local PostgreSQL and processed by the local LLM, with no transmission to an external service

### Requirement: PostgreSQL backup and restore

The deployment SHALL provide a defined backup and restore procedure for the PostgreSQL data on `gb10.local`.

#### Scenario: Backup can be restored

- **WHEN** a backup is taken and later restored to a fresh PostgreSQL instance
- **THEN** the application starts against the restored database with its data intact
