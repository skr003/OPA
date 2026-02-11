resource "azurerm_storage_account" "good_storage" {
  name                     = "secopsgoodstore"  # Ensure this name is globally unique!
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # -------------------------------------------------------------
  # SECURITY CONTROLS (CIS COMPLIANT)
  # -------------------------------------------------------------

  # 1. Disable Public Blob Access (Replaces 'allow_blob_public_access' in v4)
  allow_nested_items_to_be_public = false

  # 2. Infrastructure Encryption (Double Encryption)
  # Note: Requires 'GeneralPurposeV2' (default).
  infrastructure_encryption_enabled = true

  # 3. Network Security (Firewall)
  # We allow public access to the resource itself, but restrict it via firewall rules.
  public_network_access_enabled = true

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices", "Logging", "Metrics"]
    
    # Add your own public IP here if you need to access it from your machine
    # ip_rules       = ["203.0.113.1"] 
  }

  # 4. Soft Delete (Data Recovery)
  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }

  # 5. Logging (Audit Trail)
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
