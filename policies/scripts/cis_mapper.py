import json
import os

def generate_fix(input_file, output_file):
    # Check if file exists before opening
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found in {os.getcwd()}")
        return

    with open(input_file, 'r') as f:
        data = json.load(f)

    # Change to .bat for Windows remediation
    with open("remediate_drift.bat", "w") as f:
        f.write("@echo off\n")
        for item in data:
            name = item['name']
            rg = item['resourceGroup']
            print(f"Generating fix for: {name}")
            # Windows-friendly az command
            f.write(f"call az storage account update --name {name} --resource-group {rg} --allow-blob-public-access false\n")

if __name__ == "__main__":
    # We look for the JSON in the parent directory (workspace root)
    # or just use the filename if running from the root.
    generate_fix("drift_results.json", "remediate_drift.bat")
