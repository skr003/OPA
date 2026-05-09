"""Stage 3 – Query Azure Resource Graph for all 4 scenarios and save raw JSON."""
import json, subprocess, os, sys
from datetime import datetime, timezone, timedelta

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

def run_az(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("AZ ERROR:", r.stderr.strip())
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None

def save(name, data):
    path = os.path.join(OUTPUTS, f"{name}_raw.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path

def main():
    os.makedirs(OUTPUTS, exist_ok=True)
    errors = 0

    # --- Scenario 1: NSG inbound rules ---
    print("[Query] NSG inbound allow rules...")
    nsg_kql = (
        "Resources"
        " | where type =~ 'Microsoft.Network/networkSecurityGroups'"
        " | mv-expand rules = properties.securityRules"
        " | where rules.properties.direction =~ 'Inbound'"
        "   and rules.properties.access =~ 'Allow'"
        " | project id, name, resourceGroup,"
        "   ruleName=tostring(rules.name),"
        "   port=tostring(rules.properties.destinationPortRange),"
        "   source=tostring(rules.properties.sourceAddressPrefix)"
    )
    nsg = run_az(f'az graph query -q "{nsg_kql}" --output json') or {"data": []}
    save("nsg", nsg)
    print(f"  -> {len(nsg.get('data', []))} inbound rules captured")

    # --- Scenario 2: Storage accounts missing HTTPS-only ---
    print("[Query] Storage accounts with insecure settings...")
    storage_kql = (
        "Resources"
        " | where type =~ 'Microsoft.Storage/storageAccounts'"
        " | where properties.supportsHttpsTrafficOnly == false"
        "    or properties.allowBlobPublicAccess == true"
        " | project id, name, resourceGroup,"
        "   httpsOnly=tostring(properties.supportsHttpsTrafficOnly),"
        "   publicBlob=tostring(properties.allowBlobPublicAccess)"
    )
    storage = run_az(f'az graph query -q "{storage_kql}" --output json') or {"data": []}
    save("storage", storage)
    print(f"  -> {len(storage.get('data', []))} non-compliant accounts captured")

    # --- Scenario 3: VM sizes ---
    print("[Query] Virtual machine hardware profiles...")
    scaling_kql = (
        "Resources"
        " | where type =~ 'Microsoft.Compute/virtualMachines'"
        " | project id, name, resourceGroup,"
        "   vmSize=tostring(properties.hardwareProfile.vmSize)"
    )
    scaling = run_az(f'az graph query -q "{scaling_kql}" --output json') or {"data": []}
    save("scaling", scaling)
    print(f"  -> {len(scaling.get('data', []))} VMs captured")

    # --- Scenario 4: IAM role assignments + activity log ---
    print("[Query] IAM role assignments and activity log (last 24 h)...")
    start = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    activity = run_az(
        f'az monitor activity-log list --start-time "{start}"'
        f' --query "[?authorization.action == \'Microsoft.Authorization/roleAssignments/write\']"'
        f' --output json'
    ) or []
    assignments = run_az(
        "az role assignment list --all --include-inherited --output json"
    ) or []
    save("iam", {"activity": activity, "assignments": assignments})
    print(f"  -> {len(assignments)} assignments, {len(activity)} recent IAM changes captured")

    print(f"\n[Query] All resource queries complete. Raw data saved to outputs/")
    sys.exit(errors)

if __name__ == "__main__":
    main()
