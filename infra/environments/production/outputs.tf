output "resource_group_name" {
  description = "Name of the production resource group"
  value       = module.main.resource_group_name
}

output "resource_group_location" {
  description = "Location of the production resource group"
  value       = module.main.resource_group_location
}
