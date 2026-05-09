package policy.vm_size

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# -----------------------------------------------------------------------------
# SCENARIO 3 — Cost governance: enforce permitted VM sizes per environment.
#
# env_config.json is passed to OPA via -d and merges into data.config.
# A developer choosing an oversized VM in 'dev' to speed up testing is
# technically secure but violates company cost policy — this rule blocks it.
# -----------------------------------------------------------------------------

permitted_sizes := {
    "dev": {
        "Standard_B1s",    "Standard_B2s",    "Standard_B2ms",
        "Standard_B4ms",   "Standard_D2s_v3", "Standard_D4s_v3"
    },
    "staging": {
        "Standard_B2s",    "Standard_B4ms",   "Standard_D2s_v3",
        "Standard_D4s_v3", "Standard_D8s_v3"
    },
    "prod": {
        "Standard_D2s_v3",  "Standard_D4s_v3",  "Standard_D8s_v3",
        "Standard_D16s_v3", "Standard_E4s_v3",  "Standard_E8s_v3",
        "Standard_E16s_v3"
    }
}

new_vm_types := {
    "azurerm_linux_virtual_machine",
    "azurerm_windows_virtual_machine"
}

# New-style VM resources (azurerm_linux/windows_virtual_machine) use 'size'
deny contains msg if {
    resource := input.planned_values.root_module.resources[_]
    resource.type in new_vm_types
    vm_size  := resource.values.size
    env      := data.config.environment
    allowed  := permitted_sizes[env]
    not allowed[vm_size]
    msg := sprintf(
        "COST POLICY VIOLATION: '%s' uses VM size '%s' which is not permitted in the '%s' environment.",
        [resource.address, vm_size, env]
    )
}

# Legacy VM resources (azurerm_virtual_machine) use 'vm_size'
deny contains msg if {
    resource := input.planned_values.root_module.resources[_]
    resource.type == "azurerm_virtual_machine"
    vm_size  := resource.values.vm_size
    env      := data.config.environment
    allowed  := permitted_sizes[env]
    not allowed[vm_size]
    msg := sprintf(
        "COST POLICY VIOLATION: '%s' uses VM size '%s' which is not permitted in the '%s' environment.",
        [resource.address, vm_size, env]
    )
}
