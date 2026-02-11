resource "azurerm_storage_account" "good_storage" {
  # -------------------------------------------------------------
  # FALSE POSITIVE HANDLING (AzureRM v4.0 Defaults)
  # -------------------------------------------------------------
  #tfsec:ignore:AVD-AZU-0010 
  #tfsec:ignore:AVD-AZU-0011

  name                     = "secopsgoodstore"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  min_tls_version          = "TLS1_2"

  # Disable Public Access
  allow_nested_items_to_be_public = false

  # Infrastructure Encryption
  infrastructure_encryption_enabled = true

  # Network Security
  public_network_access_enabled = true
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices", "Logging", "Metrics"]
    ip_rules       = ["100.0.0.1"] 
  }

  # Data Recovery
  blob_properties {
    delete_retention_policy { days = 7 }
    container_delete_retention_policy { days = 7 }
    versioning_enabled = true
  }

  # Audit Logging
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
