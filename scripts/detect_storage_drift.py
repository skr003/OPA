"""Scenario 2 – Data Exfiltration: Storage accounts without HTTPS-only."""
import json, subprocess, sys, os
from datetime import datetime, timezone

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

def run_az(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("AZ ERROR:", r.stderr.strip())
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None

def main():
    print("[Storage] Querying for accounts with HTTPS-only disabled...")
    kql = (
        "Resources"
        " | where type =~ 'Microsoft.Storage/storageAccounts'"
        " | where properties.supportsHttpsTrafficOnly == false"
        "    or properties.allowBlobPublicAccess == true"
        " | project id, name, resourceGroup,"
        "   httpsOnly=tostring(properties.supportsHttpsTrafficOnly),"
        "   publicBlob=tostring(properties.allowBlobPublicAccess)"
    )
    raw = run_az(f'az graph query -q "{kql}" --output json')
    data = raw.get("data", []) if raw else []

    drifted = []
    for row in data:
        violations = []
        if row.get("httpsOnly", "").lower() != "true":
            violations.append("HTTPS-only disabled (CIS 3.15)")
        if row.get("publicBlob", "").lower() == "true":
            violations.append("Public blob access enabled (CIS 3.5)")
        drifted.append({
            "name"          : row.get("name"),
            "resource_group": row.get("resourceGroup"),
            "violations"    : violations,
            "severity"      : "HIGH"
        })

    result = {
        "scenario"     : "storage_https",
        "description"  : "Storage accounts allowing insecure HTTP or public blob access",
        "detected_at"  : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "drifted"      : len(drifted) > 0,
        "drifted_count": len(drifted),
        "resources"    : drifted
    }
    with open(os.path.join(OUTPUTS, "storage_drift.json"), "w") as f:
        json.dump(result, f, indent=2)

    bat_path = os.path.join(OUTPUTS, "storage_remediate.bat")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo [Storage] Enforcing HTTPS-only and disabling public blob access...\n")
        for r in drifted:
            name = r["name"]
            rg   = r["resource_group"]
            f.write(f'call az storage account update --name {name} --resource-group {rg} --https-only true --allow-blob-public-access false\n')
        f.write("echo [Storage] Remediation complete.\n")

    if drifted:
        print(f"[Storage] DRIFT DETECTED — {len(drifted)} account(s). Awaiting approval.")
        sys.exit(1)
    print("[Storage] COMPLIANT — all storage accounts use HTTPS-only.")
    sys.exit(0)

if __name__ == "__main__":
    main()
