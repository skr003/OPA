variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "rg-security-lab"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "East US"
}

variable "prefix" {
  description = "Short prefix applied to every resource name for uniqueness"
  type        = string
  default     = "secops"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod). Controls OPA VM-size allowlist."
  type        = string
  default     = "dev"
}

variable "cost_center" {
  description = "Cost centre tag applied to every resource for financial attribution"
  type        = string
  default     = "security-lab"
}

variable "vm_size" {
  description = "VM SKU for the Linux virtual machine. Must be in the OPA allowlist for the chosen environment."
  type        = string
  default     = "Standard_B2s"  # allowed in dev and staging per policies/vm_size.rego
}

variable "admin_username" {
  description = "Local administrator username for the Linux VM"
  type        = string
  default     = "azureuser"
}

variable "admin_password" {
  description = "Local administrator password for the Linux VM (used only when SSH key auth is disabled)"
  type        = string
  sensitive   = true
  default     = "ChangeMe123!"  # Override via TF_VAR_admin_password in production
}
