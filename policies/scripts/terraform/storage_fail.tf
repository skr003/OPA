resource "azurerm_storage_account" "bad_storage" {
  name                     = "secopsbadstore" 
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # -------------------------------------------------------------
  # VIOLATION: PUBLIC ACCESS ENABLED
  # This triggers tfsec Rule AZU012 -> High Severity -> OPA BLOCK
  # -------------------------------------------------------------
  allow_nested_items_to_be_public = true  # <--- The "Red Flag"

  # VIOLATION: No Network Rules (Open to 0.0.0.0/0)
  public_network_access_enabled = true
  
  tags = {
    Environment = "Security-Lab"
    Status      = "Vulnerable"
  }
}
