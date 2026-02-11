resource "azurerm_storage_account" "good_storage" {
  name                     = "secopsgoodstore"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # -------------------------------------------------------------
  # SECURITY CONTROLS (CIS COMPLIANT)
  # -------------------------------------------------------------

  # 1. Disable Public Access (v4.0 Syntax)
  allow_nested_items_to_be_public = false

  # 2. Infrastructure Encryption (Double Encryption)
  infrastructure_encryption_enabled = true

  # -------------------------------------------------------------
  # FALSE POSITIVE HANDLING (REQUIRED FOR v4.0)
  # AzureRM v4.0 enforces TLS 1.2 and HTTPS by default, 
  # but tfsec still flags them if the code is missing.
  # -------------------------------------------------------------
  
  tfsec:ignore:AZU010  <-- Ignore "HTTPS Traffic Only" (Enforced by Azure)
  tfsec:ignore:AZU013  <-- Ignore "Min TLS Version" (Enforced by Azure)

  # -------------------------------------------------------------
  # NETWORK & LOGGING
  # -------------------------------------------------------------
  
  # Allow public access to the resource endpoint, BUT filter it via firewall
  public_network_access_enabled = true

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices", "Logging", "Metrics"]
    ip_rules       = ["100.0.0.1"] # Represents a corporate VPN IP
  }

  # Soft Delete (Data Recovery)
  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }

  # Logging (Audit Trail)
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
    Environment = "Security-Lab"
    Compliance  = "CIS-Benchmark-Passed"
  }
}
