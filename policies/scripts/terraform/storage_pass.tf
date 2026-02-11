resource "azurerm_storage_account" "good_storage" {
  name                     = "secopsgoodstore"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  
  # Standard/GRS for redundancy
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # -------------------------------------------------------------
  # 1. PUBLIC ACCESS & ENCRYPTION (CIS 3.1, 3.6, 3.10)
  # -------------------------------------------------------------
  # v4.0 syntax for "No Public Access"
  allow_nested_items_to_be_public = false
  
  # Double Encryption (Infrastructure + Service) - CIS Best Practice
  infrastructure_encryption_enabled = true

  # NOTE: 'enable_https_traffic_only' and 'min_tls_version' are 
  # intentionally OMITTED because AzureRM v4.0+ forces them to 
  # 'true' and 'TLS1_2' by default. You cannot disable them.

  # -------------------------------------------------------------
  # 2. NETWORK SECURITY (CIS 3.7 / AZU011)
  # -------------------------------------------------------------
  # Firewall: Deny traffic from the public internet by default.
  # Only allow traffic from specific IPs or Azure Services.
  public_network_access_enabled = true # Must be true to allow specific IPs below

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices", "Logging", "Metrics"]
    ip_rules       = ["100.0.0.1"] # Example: Your Corporate VPN IP
  }

  # -------------------------------------------------------------
  # 3. DATA PROTECTION / RECOVERY (CIS 3.8 / AZU007)
  # -------------------------------------------------------------
  # Enable Soft Delete (Recycle Bin) for Blobs
  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
    versioning_enabled = true
  }

  # -------------------------------------------------------------
  # 4. LOGGING & AUDITING (CIS 3.5 / AZU016)
  # -------------------------------------------------------------
  # Enable Logging for Queue Services
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
    Compliance  = "CIS-Benchmark"
  }
}
