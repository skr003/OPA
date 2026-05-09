output "resource_group_name" {
  description = "Name of the deployed resource group"
  value       = azurerm_resource_group.main.name
}

output "secure_storage_id" {
  description = "Resource ID of the CIS-compliant storage account"
  value       = azurerm_storage_account.secure.id
}

output "vulnerable_storage_id" {
  description = "Resource ID of the intentionally non-compliant storage account (demo violations)"
  value       = azurerm_storage_account.vulnerable.id
}

output "vm_id" {
  description = "Resource ID of the Linux VM — exercises OPA vm_size policy"
  value       = azurerm_linux_virtual_machine.main.id
}

output "vm_size" {
  description = "Deployed VM size — must be on the OPA allowlist for the active environment"
  value       = azurerm_linux_virtual_machine.main.size
}

output "nsg_id" {
  description = "Resource ID of the Network Security Group"
  value       = azurerm_network_security_group.main.id
}
