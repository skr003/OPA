# -------------------------------------------------------------
# SECURE STORAGE ACCOUNT (Will Pass tfsec/Checkov)
# Fixes:
# 1. Public access disabled
# 2. Enforced HTTPS
# 3. Enforced TLS 1.2
# 4. Network rules deny internet traffic by default
# -------------------------------------------------------------

resource "azurerm_storage_account" "good_storage" {
  name                     = "${var.prefix}goodstore"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # SECURITY FIXES HERE:
  allow_blob_public_access  = false         # <--- SECURE
  enable_https_traffic_only = true          # <--- SECURE
  min_tls_version           = "TLS1_2"      # <--- SECURE
  
  # Network restriction (Optional but recommended for passing 'Network' checks)
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = {
    environment = "prod"
    compliance  = "cis-azure"
  }
}
