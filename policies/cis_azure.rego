package cis.azure

import future.keywords.contains
import future.keywords.if

# -----------------------------------------------------------------------------
# CONFIGURATION: EXCEPTION LIST (Bypass Mechanism)
# Add the names of resources allowed to break the rules here.
# -----------------------------------------------------------------------------
exception_list := {
    "azurerm_storage_account.public_website_assets", 
    "azurerm_storage_account.legacy_app_data"
}

# Helper to check if a resource is on the exception list
is_exempt(resource_name) {
    exception_list[resource_name]
}

# -----------------------------------------------------------------------------
# RULE 1: Ensure 'Secure Transfer Required' is Enabled (HTTPS)
# CIS Benchmark 3.1 / tfsec: AZU010
# -----------------------------------------------------------------------------
deny contains msg if {
    result := input.results[_]
    result.rule_id == "AZU010"
    not is_exempt(result.resource)  # <--- The Bypass Check

    msg := sprintf("CIS 3.1 VIOLATION: Secure transfer (HTTPS) is disabled on '%s'.", [result.resource])
}

# -----------------------------------------------------------------------------
# RULE 2: Ensure 'Allow Blob Public Access' is Disabled
# CIS Benchmark 3.6 / tfsec: AZU012
# -----------------------------------------------------------------------------
deny contains msg if {
    result := input.results[_]
    result.rule_id == "AZU012"
    not is_exempt(result.resource)

    msg := sprintf("CIS 3.6 VIOLATION: Public blob access is enabled on '%s'.", [result.resource])
}

# -----------------------------------------------------------------------------
# RULE 3: Ensure Default Network Access Rule is 'Deny'
# CIS Benchmark 3.7 / tfsec: AZU011
# -----------------------------------------------------------------------------
deny contains msg if {
    result := input.results[_]
    result.rule_id == "AZU011"
    not is_exempt(result.resource)

    msg := sprintf("CIS 3.7 VIOLATION: Storage account '%s' does not deny network traffic by default.", [result.resource])
}

# -----------------------------------------------------------------------------
# RULE 4: Ensure Minimum TLS Version is set to 1.2
# CIS Benchmark 3.10 / tfsec: AZU013
# -----------------------------------------------------------------------------
deny contains msg if {
    result := input.results[_]
    result.rule_id == "AZU013"
    not is_exempt(result.resource)

    msg := sprintf("CIS 3.10 VIOLATION: TLS version is outdated on '%s'. Must be 1.2.", [result.resource])
}

# -----------------------------------------------------------------------------
# RULE 5: Ensure 'Infrastructure Encryption' is Enabled
# CIS Benchmark 3.2 / tfsec: AZU014
# -----------------------------------------------------------------------------
deny contains msg if {
    result := input.results[_]
    result.rule_id == "AZU014"
    not is_exempt(result.resource)

    msg := sprintf("CIS 3.2 VIOLATION: Infrastructure encryption is disabled on '%s'.", [result.resource])
}
