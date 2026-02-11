resource "azurerm_storage_account" "bad_storage" {
  # -------------------------------------------------------------
  # FALSE POSITIVE HANDLING (AzureRM v4.0 Defaults)
  # -------------------------------------------------------------
  #tfsec:ignore:AVD-AZU-0010 
  #tfsec:ignore:AVD-AZU-0011

  name                     = "secopsbadstore" 
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # -------------------------------------------------------------
  # THE DEMO VIOLATION: PUBLIC ACCESS ENABLED
  # -------------------------------------------------------------
  allow_nested_items_to_be_public = true  # <--- The "Red Flag"

  public_network_access_enabled = true
  
  tags = {
    Environment = "Security-Lab"
    Status      = "Vulnerable"
  }
}
