# -------------------------------------------------------------
# INSECURE STORAGE ACCOUNT (Will Fail tfsec/Checkov)
# Violations:
# 1. allow_blob_public_access is TRUE (CIS 3.1)
# 2. enable_https_traffic_only is FALSE (CIS 3.2)
# 3. min_tls_version is "TLS1_0" (Should be TLS1_2)
# -------------------------------------------------------------

resource "azurerm_storage_account" "bad_storage" {
  name                     = "${var.prefix}badstore"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # SECURITY FLAWS HERE:
  allow_nested_items_to_be_public  = false          # <--- VIOLATION!
  enable_https_traffic_only = true         # <--- VIOLATION!
  min_tls_version           = "TLS1_2"      # <--- VIOLATION!
  
  tags = {
    environment = "dev"
    compliance  = "none"
  }
}
