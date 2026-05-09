package policy.tags

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# -----------------------------------------------------------------------------
# SCENARIO 4 — Governance enforcement: every tracked resource must carry all
# mandatory tags before it is allowed to deploy.
#
# Missing tags mean broken cost attribution (CostCenter) and untraceable
# resources in production.  This rule catches the omission at PR time,
# not after the resource has been live for weeks.
# -----------------------------------------------------------------------------

required_tags := {
    "Environment",
    "CostCenter",
    "ManagedBy"
}

# Extend this set as new resource types are introduced to the codebase.
taggable_types := {
    "azurerm_resource_group",
    "azurerm_storage_account",
    "azurerm_linux_virtual_machine",
    "azurerm_windows_virtual_machine",
    "azurerm_virtual_machine",
    "azurerm_key_vault",
    "azurerm_sql_server",
    "azurerm_app_service"
}

deny contains msg if {
    resource := input.planned_values.root_module.resources[_]
    resource.type in taggable_types
    tag      := required_tags[_]
    not resource.values.tags[tag]
    msg := sprintf(
        "GOVERNANCE VIOLATION: Resource '%s' (%s) is missing mandatory tag '%s'.",
        [resource.address, resource.type, tag]
    )
}
