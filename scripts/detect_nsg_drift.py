"""Scenario 1 – Rogue Admin: open SSH/RDP ports on NSGs."""
import json, subprocess, sys, os
from datetime import datetime, timezone

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
DANGEROUS_PORTS = {"22", "3389", "*"}
OPEN_SOURCES    = {"*", "internet", "0.0.0.0/0", "any"}

def run_az(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("AZ ERROR:", r.stderr.strip())
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None

def main():
    raw_path = os.path.join(OUTPUTS, "nsg_raw.json")
    if os.path.exists(raw_path):
        print("[NSG] Reading pre-queried data from nsg_raw.json...")
        with open(raw_path) as f:
            data = json.load(f).get("data", [])
    else:
        print("[NSG] Querying Azure Resource Graph for open SSH/RDP rules...")
        kql = (
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
        raw = run_az(f'az graph query -q "{kql}" --output json')
        data = raw.get("data", []) if raw else []

    drifted = []
    for row in data:
        port   = (row.get("port") or "").strip()
        source = (row.get("source") or "").strip().lower()
        if port in DANGEROUS_PORTS and source in OPEN_SOURCES:
            drifted.append({
                "nsg_name"     : row.get("name"),
                "resource_group": row.get("resourceGroup"),
                "rule_name"    : row.get("ruleName"),
                "port"         : port,
                "source"       : row.get("source"),
                "cis_control"  : "CIS 6.1 / CIS 6.2",
                "severity"     : "CRITICAL"
            })

    result = {
        "scenario"    : "nsg_open_ports",
        "description" : "NSG rules exposing SSH (22) or RDP (3389) to the internet",
        "detected_at" : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "drifted"     : len(drifted) > 0,
        "drifted_count": len(drifted),
        "resources"   : drifted
    }
    with open(os.path.join(OUTPUTS, "nsg_drift.json"), "w") as f:
        json.dump(result, f, indent=2)

    # Remediation script: update offending rules to Deny
    bat_path = os.path.join(OUTPUTS, "nsg_remediate.bat")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo [NSG] Closing unauthorized inbound rules...\n")
        for r in drifted:
            f.write(
                f'call az network nsg rule update'
                f' --resource-group {r["resource_group"]}'
                f' --nsg-name {r["nsg_name"]}'
                f' --name {r["rule_name"]}'
                f' --access Deny\n'
            )
        f.write("echo [NSG] Self-healing complete.\n")

    if drifted:
        print(f"[NSG] DRIFT DETECTED — {len(drifted)} open rule(s). Remediation script written.")
        sys.exit(1)
    print("[NSG] COMPLIANT — no open SSH/RDP rules found.")
    sys.exit(0)

if __name__ == "__main__":
    main()
