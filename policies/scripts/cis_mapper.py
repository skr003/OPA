import json
import sys

# Define mapping: Resource Issue -> CIS Control ID -> Remediation Command
CIS_MAP = {
    "Microsoft.Storage/storageAccounts": {
        "issue": "allowBlobPublicAccess",
        "cis_id": "CIS 3.1",
        "fix_cmd": "az storage account update --name {name} --resource-group {rg} --allow-blob-public-access false"
    }
}

def generate_fix(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    with open(output_file, 'w') as out:
        if not data:
            print("No drift found.")
            return

        out.write("#!/bin/bash\n")
        out.write("# Auto-Generated Remediation Script\n")
        
        for resource in data:
            # Assuming the query filters for the specific issue
            rule = CIS_MAP["Microsoft.Storage/storageAccounts"]
            
            cmd = rule["fix_cmd"].format(
                name=resource['name'], 
                rg=resource['resourceGroup']
            )
            
            out.write(f"echo 'Remediating {rule['cis_id']} on {resource['name']}...'\n")
            out.write(cmd + "\n")
            
    print(f"Remediation script generated: {output_file}")

if __name__ == "__main__":
    # Simplified argument handling for demo
    generate_fix("drift_results.json", "remediation_script.sh")
