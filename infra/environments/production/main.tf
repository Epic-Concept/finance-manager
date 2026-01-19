# Production Environment Configuration

terraform {
  required_version = ">= 1.5.0"

  # Uncomment and configure backend for state storage
  # backend "azurerm" {
  #   resource_group_name  = "terraform-state-rg"
  #   storage_account_name = "tfstatefinancemanager"
  #   container_name       = "tfstate"
  #   key                  = "production.terraform.tfstate"
  # }
}

module "main" {
  source = "../../"

  resource_group_name = "finance-manager-prod-rg"
  location            = "westeurope"
  environment         = "production"

  tags = {
    project     = "finance-manager"
    environment = "production"
    managed_by  = "terraform"
  }
}
