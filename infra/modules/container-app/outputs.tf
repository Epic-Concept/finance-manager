output "environment_id" {
  description = "ID of the Container App Environment"
  value       = azurerm_container_app_environment.main.id
}

output "api_fqdn" {
  description = "FQDN of the API container app"
  value       = azurerm_container_app.api.latest_revision_fqdn
}

output "web_fqdn" {
  description = "FQDN of the web container app"
  value       = azurerm_container_app.web.latest_revision_fqdn
}
