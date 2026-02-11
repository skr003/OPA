# -------------------------------------------------------------
# CORE INFRASTRUCTURE CONFIGURATION
# This file sets up the provider and the base Resource Group.
# -------------------------------------------------------------

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 3.116.0"
    }
  }
  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}
  # Explicitly allowing registration of necessary resource providers
  skip_provider_registration = false
}

# -------------------------------------------------------------
# SHARED RESOURCE GROUP
# All storage accounts (secure & insecure) will be deployed here.
# -------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = "Security-Lab"
    ManagedBy   = "Terraform"
    Project     = "Azure-CIS-Compliance"
  }
}
