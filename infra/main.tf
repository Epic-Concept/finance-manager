terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85.0"
    }
  }
}

provider "azurerm" {
  features {}

  # Note: Authentication should be configured via environment variables:
  # - ARM_CLIENT_ID
  # - ARM_CLIENT_SECRET
  # - ARM_SUBSCRIPTION_ID
  # - ARM_TENANT_ID
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}
