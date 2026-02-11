resource "azurerm_storage_account" "bad_storage" {
  name                     = "secopsbadstore" 
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # -------------------------------------------------------------
  # IGNORE NOISE (TLS False Positive)
  # -------------------------------------------------------------
  #tfsec:ignore:AVD-AZU-0011

  # -------------------------------------------------------------
  # THE REAL DEMO VIOLATION
  # This is the specific line we want OPA to block!
  # -------------------------------------------------------------
  allow_nested_items_to_be_public = true 

  public_network_access_enabled = true
  
  tags = {
    Environment = "Security-Lab"
    Status      = "Vulnerable"
  }
}
