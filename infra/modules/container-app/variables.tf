variable "environment_name" {
  description = "Name of the Container App Environment"
  type        = string
}

variable "app_name" {
  description = "Base name for the container apps"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "api_image" {
  description = "Docker image for the API"
  type        = string
}

variable "web_image" {
  description = "Docker image for the web app"
  type        = string
}

variable "api_cpu" {
  description = "CPU allocation for API container"
  type        = number
  default     = 0.5
}

variable "api_memory" {
  description = "Memory allocation for API container"
  type        = string
  default     = "1Gi"
}

variable "web_cpu" {
  description = "CPU allocation for web container"
  type        = number
  default     = 0.25
}

variable "web_memory" {
  description = "Memory allocation for web container"
  type        = string
  default     = "0.5Gi"
}

variable "min_replicas" {
  description = "Minimum number of replicas"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum number of replicas"
  type        = number
  default     = 3
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
