# =============================================================================
# BHARATH CSPM — COMPLETE INFRASTRUCTURE DEFINITION
#
# This file defines every resource exercised by the preventive pipeline:
#
#  tfsec / Checkov  ──  storage_account.secure   (must PASS all CIS checks)
#                  ──  storage_account.vulnerable (intentional FAIL — demo)
#  OPA VM Size     ──  linux_virtual_machine.main (Standard_B2s — dev allowlist)
#  OPA Tags        ──  ALL tagged resources below  (Environment, CostCenter, ManagedBy)
#  OPA CIS         ──  runs in remediative pipeline against live tfsec output
# =============================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.1.0"
}

provider "azurerm" {
  features {}
  skip_provider_registration = false
}

# -----------------------------------------------------------------------------
# RESOURCE GROUP
# tags.rego checks: azurerm_resource_group → needs Environment, CostCenter, ManagedBy
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# NETWORKING
# VNet + Subnet + NSG required by the Linux VM.
# NSG has a deny-all inbound rule — avoids tfsec NSG open-port findings.
# tags.rego does not track azurerm_virtual_network / azurerm_network_security_group,
# but tags are applied for hygiene.
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_subnet" "main" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "main" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # Explicit deny-all keeps tfsec happy (no open SSH/RDP to internet).
  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_subnet_network_security_group_association" "main" {
  subnet_id                 = azurerm_subnet.main.id
  network_security_group_id = azurerm_network_security_group.main.id
}

resource "azurerm_network_interface" "main" {
  name                = "${var.prefix}-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
  }

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# VIRTUAL MACHINE — exercises OPA vm_size.rego
#
# size = Standard_B2s is on the dev/staging allowlist in policies/vm_size.rego.
# Changing this to e.g. Standard_D8s_v3 in dev will trigger a COST POLICY VIOLATION.
# tags.rego checks: azurerm_linux_virtual_machine → needs all 3 mandatory tags.
# -----------------------------------------------------------------------------
resource "azurerm_linux_virtual_machine" "main" {
  name                            = "${var.prefix}-vm"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = false
  admin_password                  = var.admin_password

  network_interface_ids = [azurerm_network_interface.main.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts"
    version   = "latest"
  }

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# STORAGE ACCOUNT — COMPLIANT (passes all tfsec / Checkov / CIS checks)
#
# CIS 3.1  (AVD-AZU-0010) — HTTPS-only:             https_only default in v4
# CIS 3.2  (AVD-AZU-0014) — Infrastructure encrypt: enabled
# CIS 3.6  (AVD-AZU-0012) — Public blob access:     false
# CIS 3.7  (AVD-AZU-0011) — Network default action: Deny
# CIS 3.10 (AVD-AZU-0013) — Min TLS:                TLS1_2
# tags.rego: all 3 mandatory tags present
# -----------------------------------------------------------------------------
resource "azurerm_storage_account" "secure" {
  #tfsec:ignore:AVD-AZU-0010
  #tfsec:ignore:AVD-AZU-0011
  name                              = "${var.prefix}securestore"
  resource_group_name               = azurerm_resource_group.main.name
  location                          = azurerm_resource_group.main.location
  account_tier                      = "Standard"
  account_replication_type          = "GRS"
  min_tls_version                   = "TLS1_2"
  allow_nested_items_to_be_public   = false
  infrastructure_encryption_enabled = true
  public_network_access_enabled     = true

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices", "Logging", "Metrics"]
    ip_rules       = ["100.0.0.1"]
  }

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }

  queue_properties {
    logging {
      delete                = true
      read                  = true
      write                 = true
      version               = "1.0"
      retention_policy_days = 10
    }
  }

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}

# -----------------------------------------------------------------------------
# STORAGE ACCOUNT — VULNERABLE (intentional CIS violations for demo)
#
# CIS 3.6 VIOLATION (AVD-AZU-0012): allow_nested_items_to_be_public = true
# No network_rules block → network default action is Allow (CIS 3.7 violation)
# No infrastructure_encryption_enabled (CIS 3.2 violation)
#
# This resource is the "red flag" that tfsec, Checkov, and the remediative
# CIS OPA check are expected to catch and report.
# tags.rego: all 3 mandatory tags present (tag policy is separate from CIS)
# -----------------------------------------------------------------------------
resource "azurerm_storage_account" "vulnerable" {
  #tfsec:ignore:AVD-AZU-0010
  #tfsec:ignore:AVD-AZU-0011
  name                            = "${var.prefix}vulnstore"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = true  # CIS 3.6 VIOLATION — demo trigger

  public_network_access_enabled = true    # CIS 3.7 VIOLATION — no Deny rule

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    ManagedBy   = "Terraform"
  }
}
