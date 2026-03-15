import json
import os
import sys

def generate_fix(input_file, output_filename):
    # Step 1: Find the Root Workspace (Parent of 'policies/scripts')
    # This ensures the .bat file is saved in the root for Jenkins to find.
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    input_path = os.path.join(base_dir, input_file)
    output_path = os.path.join(base_dir, output_filename)

    print(f"Looking for data in: {input_path}")

    if not os.path.exists(input_path):
        print(f"CRITICAL ERROR: {input_file} not found in {base_dir}")
        sys.exit(1)

    with open(input_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("ERROR: JSON file is empty or corrupted.")
            return

    # Step 2: Write the Windows Batch script to the root
    with open(output_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo Starting Remediation for CIS 3.1 Violation...\n")
        
        if not data:
            f.write("echo No drifting resources found. Infrastructure is compliant.\n")
        else:
            for item in data:
                name = item['name']
                rg = item['resourceGroup']
                print(f"Mapping remediation for: {name}")
                # Using 'call az' ensures the script continues if there are multiple resources
                f.write(f"call az storage account update --name {name} --resource-group {rg} --allow-blob-public-access false\n")
        
        f.write("echo Remediation Complete.\n")
    
    print(f"SUCCESS: Remediation script generated at {output_path}")

if __name__ == "__main__":
    generate_fix("drift_results.json", "remediate_drift.bat")
