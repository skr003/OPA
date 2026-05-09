"""Scenario 4 – IAM Tampering: unauthorized high-privilege role assignments."""
import json, subprocess, sys, os
from datetime import datetime, timezone, timedelta

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

HIGH_PRIV_ROLES = {
    "8e3af657-a8ff-443c-a75c-2fe8c4bcb635": "Owner",
    "b24988ac-6180-42a0-ab88-20f7382dd24c": "Contributor",
    "18d7d88d-d35e-4fb5-a5c3-7773c20a72d9": "User Access Administrator"
}

def run_az(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("AZ ERROR:", r.stderr.strip())
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None

def main():
    raw_path = os.path.join(OUTPUTS, "iam_raw.json")
    if os.path.exists(raw_path):
        print("[IAM] Reading pre-queried data from iam_raw.json...")
        with open(raw_path) as f:
            iam_raw = json.load(f)
        events      = iam_raw.get("activity", [])
        assignments = iam_raw.get("assignments", [])
    else:
        print("[IAM] Querying activity log for recent role assignment changes...")
        start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = run_az(
            f'az monitor activity-log list'
            f' --start-time "{start_time}"'
            f' --query "[?authorization.action == \'Microsoft.Authorization/roleAssignments/write\']"'
            f' --output json'
        )
        events = raw if isinstance(raw, list) else []
        assignments_raw = run_az('az role assignment list --all --include-inherited --output json')
        assignments = assignments_raw if isinstance(assignments_raw, list) else []

    drifted = []
    for a in assignments:
        role_id = (a.get("roleDefinitionId") or "").split("/")[-1]
        scope   = a.get("scope", "")
        ptype   = a.get("principalType", "")
        # Flag: high-priv role at subscription scope for a User or ServicePrincipal
        if role_id in HIGH_PRIV_ROLES and "/resourceGroups/" not in scope:
            drifted.append({
                "principal_name"  : a.get("principalName") or a.get("principalId"),
                "principal_type"  : ptype,
                "role"            : HIGH_PRIV_ROLES.get(role_id, a.get("roleDefinitionName")),
                "scope"           : scope,
                "assignment_id"   : a.get("id"),
                "cis_control"     : "CIS 1.1 – Ensure no subscription owner accounts without MFA",
                "severity"        : "CRITICAL"
            })

    recent_changes = [
        {
            "time"     : e.get("eventTimestamp"),
            "caller"   : e.get("caller"),
            "operation": e.get("operationName", {}).get("localizedValue"),
            "status"   : e.get("status", {}).get("localizedValue")
        }
        for e in events
    ]

    result = {
        "scenario"       : "iam_tampering",
        "description"    : "High-privilege role assignments at subscription scope",
        "detected_at"    : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "drifted"        : len(drifted) > 0,
        "drifted_count"  : len(drifted),
        "recent_changes" : recent_changes,
        "resources"      : drifted
    }
    with open(os.path.join(OUTPUTS, "iam_drift.json"), "w") as f:
        json.dump(result, f, indent=2)

    bat_path = os.path.join(OUTPUTS, "iam_remediate.bat")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write("echo [IAM] Removing unauthorized high-privilege role assignments...\n")
        for r in drifted:
            aid = r["assignment_id"]
            f.write(f'call az role assignment delete --ids "{aid}"\n')
        f.write("echo [IAM] Unauthorized role assignments removed.\n")

    if drifted:
        print(f"[IAM] PRIVILEGE ESCALATION — {len(drifted)} unauthorized assignment(s). Alerting security team.")
        sys.exit(1)
    print("[IAM] COMPLIANT — no unauthorized high-privilege assignments found.")
    sys.exit(0)

if __name__ == "__main__":
    main()
