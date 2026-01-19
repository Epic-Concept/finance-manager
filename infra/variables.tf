variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "finance-manager-rg"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "westeurope"
}

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
  default     = "production"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    project    = "finance-manager"
    managed_by = "terraform"
  }
}
