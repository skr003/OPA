output "vulnerable_storage_id" {
  description = "The ID of the insecure storage account"
  value       = azurerm_storage_account.bad_storage.id
}

output "secure_storage_id" {
  description = "The ID of the secure storage account"
  value       = azurerm_storage_account.good_storage.id
}

output "security_status" {
  value = "Run 'tfsec .' to see the difference between these two resources."
}
