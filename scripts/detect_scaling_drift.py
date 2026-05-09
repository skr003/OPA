"""Scenario 3 – Cost Control: VMs scaled outside the approved IaC baseline."""
import json, subprocess, sys, os
from datetime import datetime, timezone

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

# Approved VM sizes defined in Terraform baseline (dev environment)
APPROVED_SIZES = {
    "Standard_B1s", "Standard_B2s", "Standard_B2ms",
    "Standard_D2s_v3", "Standard_D2as_v4"
}
BASELINE_SIZE = "Standard_B2s"   # revert target

def run_az(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("AZ ERROR:", r.stderr.strip())
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None

def main():
    print("[Scaling] Querying live VM sizes against IaC baseline...")
    kql = (
        "Resources"
        " | where type =~ 'Microsoft.Compute/virtualMachines'"
        " | project id, name, resourceGroup,"
        "   vmSize=tostring(properties.hardwareProfile.vmSize)"
    )
    raw = run_az(f'az graph query -q "{kql}" --output json')
    data = raw.get("data", []) if raw else []

    drifted = []
    for row in data:
        size = row.get("vmSize", "")
        if size not in APPROVED_SIZES:
            drifted.append({
                "name"          : row.get("name"),
                "resource_group": row.get("resourceGroup"),
                "live_size"     : size,
                "baseline_size" : BASELINE_SIZE,
                "cis_control"   : "Cost Governance",
                "severity"      : "HIGH"
            })

    result = {
        "scenario"     : "resource_scaling",
        "description"  : "VMs scaled beyond approved IaC baseline sizes",
        "detected_at"  : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "drifted"      : len(drifted) > 0,
        "drifted_count": len(drifted),
        "approved_sizes": sorted(APPROVED_SIZES),
        "resources"    : drifted
    }
    with open(os.path.join(OUTPUTS, "scaling_drift.json"), "w") as f:
        json.dump(result, f, indent=2)

    # Remediation: resize back to baseline (requires VM stop/start)
    bat_path = os.path.join(OUTPUTS, "scaling_remediate.bat")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo [Scaling] Reverting VMs to IaC baseline size...\n")
        for r in drifted:
            name = r["name"]
            rg   = r["resource_group"]
            size = r["baseline_size"]
            f.write(f'call az vm deallocate --resource-group {rg} --name {name}\n')
            f.write(f'call az vm resize --resource-group {rg} --name {name} --size {size}\n')
            f.write(f'call az vm start --resource-group {rg} --name {name}\n')
        f.write("echo [Scaling] VM revert complete.\n")

    if drifted:
        print(f"[Scaling] COST DRIFT — {len(drifted)} VM(s) outside baseline. DevOps notified.")
        sys.exit(1)
    print("[Scaling] COMPLIANT — all VMs within approved sizes.")
    sys.exit(0)

if __name__ == "__main__":
    main()
