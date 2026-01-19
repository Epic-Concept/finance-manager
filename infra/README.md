# Finance Manager Infrastructure

Terraform configuration for Azure infrastructure.

## Structure

```
infra/
├── main.tf              # Main configuration
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── modules/
│   ├── database/        # PostgreSQL module
│   └── container-app/   # Container Apps module
└── environments/
    └── production/      # Production environment config
```

## Prerequisites

- Terraform >= 1.5.0
- Azure CLI authenticated
- Azure subscription

## Authentication

Set the following environment variables:

```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
```

## Usage

### Validation (CI)

```bash
# Initialize (without backend)
terraform init -backend=false

# Format check
terraform fmt -check -recursive

# Validate configuration
terraform validate
```

### Deployment (Manual)

```bash
cd environments/production

# Initialize
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan
```

## Modules

### Database Module

Provisions Azure Database for PostgreSQL Flexible Server.

### Container App Module

Provisions Azure Container Apps for API and web applications.

## Important Notes

- **CI runs validation only** - no `plan` or `apply` in automated pipelines
- Always review `terraform plan` output before applying
- Use workspaces or separate state files for different environments
