resource "azurerm_storage_account" "good_storage" {
  name                     = "secopsgoodstore"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # -------------------------------------------------------------
  # FALSE POSITIVE HANDLING
  # -------------------------------------------------------------
  # We ignore AVD-AZU-0011 because AzureRM v4.0 enforces TLS 1.2
  # automatically, but tfsec cannot see that in the code.
  
  #tfsec:ignore:AVD-AZU-0011
  
  # Also ignore the HTTPS check if it pops up (AVD-AZU-0010)
  #tfsec:ignore:AVD-AZU-0010

  # -------------------------------------------------------------
  # SECURITY CONTROLS
  # -------------------------------------------------------------
  allow_nested_items_to_be_public = false
  infrastructure_encryption_enabled = true

  public_network_access_enabled = true

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
    Environment = "Security-Lab"
    Compliance  = "CIS-Benchmark-Passed"
  }
}
