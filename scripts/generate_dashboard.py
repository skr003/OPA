"""Scenario 5 – Compliance Dashboard: aggregate all drift results into one score."""
import json, os, sys
from datetime import datetime, timezone

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")

SCENARIO_FILES = {
    "nsg_open_ports"  : "nsg_drift.json",
    "storage_https"   : "storage_drift.json",
    "resource_scaling": "scaling_drift.json",
    "iam_tampering"   : "iam_drift.json"
}

CIS_LABELS = {
    "nsg_open_ports"  : "CIS 6.1/6.2 – No open SSH/RDP to internet",
    "storage_https"   : "CIS 3.15 – Storage HTTPS-only enabled",
    "resource_scaling": "Cost Governance – VMs within IaC baseline",
    "iam_tampering"   : "CIS 1.1 – No unauthorised subscription Owner/Contributor"
}

def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "snapshot"

    scenarios = {}
    total_drifted  = 0
    total_compliant = 0

    for key, fname in SCENARIO_FILES.items():
        fpath = os.path.join(OUTPUTS, fname)
        if not os.path.exists(fpath):
            scenarios[key] = {
                "cis_label"    : CIS_LABELS[key],
                "status"       : "UNKNOWN",
                "drifted_count": 0,
                "resources"    : []
            }
            continue
        with open(fpath) as f:
            data = json.load(f)
        drifted = data.get("drifted_count", 0)
        total_drifted  += drifted
        total_compliant += (1 if drifted == 0 else 0)
        scenarios[key] = {
            "cis_label"    : CIS_LABELS[key],
            "status"       : "DRIFTED" if data.get("drifted") else "COMPLIANT",
            "drifted_count": drifted,
            "resources"    : data.get("resources", [])
        }

    total_checks = len(SCENARIO_FILES)
    compliant_scenarios = sum(1 for s in scenarios.values() if s["status"] == "COMPLIANT")
    compliance_pct = round((compliant_scenarios / total_checks) * 100)

    dashboard = {
        "phase"               : phase,
        "generated_at"        : datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_compliance_pct": compliance_pct,
        "total_scenarios"     : total_checks,
        "compliant_scenarios" : compliant_scenarios,
        "drifted_scenarios"   : total_checks - compliant_scenarios,
        "total_drifted_resources": total_drifted,
        "overall_status"      : "COMPLIANT" if compliance_pct == 100 else "DRIFTED",
        "scenarios"           : scenarios
    }

    out_file = os.path.join(OUTPUTS, f"compliance_dashboard_{phase}.json")
    with open(out_file, "w") as f:
        json.dump(dashboard, f, indent=2)

    # Always overwrite the "latest" snapshot for dashboard polling
    with open(os.path.join(OUTPUTS, "compliance_dashboard_latest.json"), "w") as f:
        json.dump(dashboard, f, indent=2)

    print(f"[Dashboard] {phase.upper()} — Compliance: {compliance_pct}%  "
          f"({compliant_scenarios}/{total_checks} scenarios clean, "
          f"{total_drifted} drifted resource(s))")

if __name__ == "__main__":
    main()
