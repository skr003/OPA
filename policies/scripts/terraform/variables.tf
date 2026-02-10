variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
  default     = "rg-security-lab"
}

variable "location" {
  description = "The Azure region to deploy to"
  type        = string
  default     = "East US"
}

variable "prefix" {
  description = "A prefix for resources to ensure uniqueness"
  type        = string
  default     = "secops"
}
