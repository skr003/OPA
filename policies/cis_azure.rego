package cis.azure

import future.keywords.contains
import future.keywords.if

# Rule: Deny Storage Accounts with Public Access (CIS 3.1)
# This rule returns a set of error messages
deny contains msg if {
    # Iterate over the finding results from tfsec
    result := input.results[_]
    
    # Check if the rule ID matches the tfsec ID for public storage
    result.rule_id == "AZU012"
    
    # Construct the failure message
    msg := sprintf("CIS_Violation (Control 3.1): Public access enabled on storage account '%s'", [result.resource])
}
