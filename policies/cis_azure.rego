package cis.azure

# Rule: Deny Storage Accounts with Public Access (CIS 3.1)
deny[msg] {
    # Input comes from tfsec (Pipeline A)
    resource := input.results[_]
    resource.rule_id == "AZU012" # tfsec ID for public storage
    
    msg := sprintf("CIS_Violation (Control 3.1): Public access enabled on storage account '%s'", [resource.resource])
}

# (Optional) Add logic here to parse Azure Resource Graph JSON for Pipeline B
