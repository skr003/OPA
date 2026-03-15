import json
import os
import sys

def generate_fix(input_file, output_filename):
    # Calculate the project root (one level up from scripts/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Path to the outputs folder
    outputs_dir = os.path.join(base_dir, "outputs")
    
    input_path = os.path.join(outputs_dir, input_file)
    output_path = os.path.join(outputs_dir, output_filename)

    print(f"Looking for data in: {input_path}")

    if not os.path.exists(input_path):
        print(f"ERROR: {input_file} not found.")
        return

    with open(input_path, 'r') as f:
        raw_payload = json.load(f)

    # FIX: Azure Graph output puts the resources inside the 'data' key
    # If the query is empty, data will be []
    resources = raw_payload.get("data", [])

    with open(output_path, "w") as f:
        f.write("@echo off\n")
        
        if not resources:
            f.write("echo [PASS] No non-compliant resources found.\n")
            print("No drift detected in Azure Resource Graph payload.")
        else:
            print(f"Found {len(resources)} resources to remediate.")
            for item in resources:
                name = item.get('name')
                rg = item.get('resourceGroup')
                if name and rg:
                    f.write(f"call az storage account update --name {name} --resource-group {rg} --allow-blob-public-access false\n")
            f.write("echo [SUCCESS] Remediation complete.\n")
    
    print(f"SUCCESS: Generated {output_path}")

if __name__ == "__main__":
    generate_fix("drift_results.json", "remediate_drift.bat")
