import json
from datetime import datetime

results = []

# ---------------------------------------------------------------------------
# tfsec — includes both passed and failed checks (--include-passed)
# ---------------------------------------------------------------------------
try:
    with open('tfsec_results.json', 'r') as f:
        tfsec_data = json.load(f)
    for r in (tfsec_data.get('results') or []):
        passed  = r.get('passed', False)
        sev     = (r.get('severity') or 'UNKNOWN').upper()
        loc     = r.get('location') or {}
        loc_str = "{}:{}".format(loc.get('filename', ''), loc.get('start_line', ''))
        desc    = r.get('description') or r.get('rule_description') or ''
        results.append({
            "tool"    : "tfsec",
            "check_id": r.get('rule_id', ''),
            "severity": sev,
            "input"   : loc_str,
            "status"  : "PASS" if passed else "FAIL",
            "reason"  : desc
        })
except Exception as e:
    results.append({
        "tool"    : "tfsec",
        "check_id": "N/A",
        "severity": "N/A",
        "input"   : "tfsec_results.json",
        "status"  : "ERROR",
        "reason"  : "Could not parse tfsec results: {}".format(e)
    })

# ---------------------------------------------------------------------------
# Checkov — separate passed_checks and failed_checks arrays
# ---------------------------------------------------------------------------
try:
    with open('checkov_results.json', 'r') as f:
        raw = f.read()
    json_start = raw.find('{')
    if json_start >= 0:
        checkov_data = json.loads(raw[json_start:])
        res = checkov_data.get('results') or {}

        for c in (res.get('passed_checks') or []):
            check   = c.get('check') or {}
            fl      = c.get('file_line_range') or [0]
            loc_str = "{}:{}".format(c.get('repo_file_path', ''), fl[0])
            results.append({
                "tool"    : "checkov",
                "check_id": c.get('check_id', ''),
                "severity": (c.get('severity') or check.get('severity') or 'N/A').upper(),
                "input"   : loc_str,
                "status"  : "PASS",
                "reason"  : check.get('name') or c.get('check_id', '')
            })

        for c in (res.get('failed_checks') or []):
            check   = c.get('check') or {}
            sev     = (c.get('severity') or check.get('severity') or 'MEDIUM').upper()
            fl      = c.get('file_line_range') or [0]
            loc_str = "{}:{}".format(c.get('repo_file_path', ''), fl[0])
            results.append({
                "tool"    : "checkov",
                "check_id": c.get('check_id', ''),
                "severity": sev,
                "input"   : loc_str,
                "status"  : "FAIL",
                "reason"  : check.get('name') or c.get('check_id', '')
            })
except Exception as e:
    results.append({
        "tool"    : "checkov",
        "check_id": "N/A",
        "severity": "N/A",
        "input"   : "checkov_results.json",
        "status"  : "ERROR",
        "reason"  : "Could not parse checkov results: {}".format(e)
    })

# ---------------------------------------------------------------------------
# OPA — one entry per check; violations become individual FAIL rows
# ---------------------------------------------------------------------------
opa_checks = [
    ('opa_cis_result.json', 'tfsec_results.json'),
    ('opa_vm_result.json',  'tfplan.json'),
    ('opa_tags_result.json','tfplan.json'),
]

for opa_file, input_file in opa_checks:
    try:
        with open(opa_file, 'r') as f:
            opa = json.load(f)

        check_name = opa.get('check', opa_file)
        status     = opa.get('status', 'UNKNOWN')

        if status == 'SKIPPED':
            results.append({
                "tool"    : "OPA",
                "check_id": check_name,
                "severity": "N/A",
                "input"   : input_file,
                "status"  : "SKIP",
                "reason"  : opa.get('reason', 'Input file unavailable')
            })
        elif status == 'PASSED':
            results.append({
                "tool"    : "OPA",
                "check_id": check_name,
                "severity": "N/A",
                "input"   : input_file,
                "status"  : "PASS",
                "reason"  : "All policy rules satisfied"
            })
        else:
            violations = opa.get('violations') or []
            if violations:
                for v in violations:
                    clean = v.strip().strip('"').rstrip(',').strip()
                    results.append({
                        "tool"    : "OPA",
                        "check_id": check_name,
                        "severity": "N/A",
                        "input"   : input_file,
                        "status"  : "FAIL",
                        "reason"  : clean
                    })
            else:
                results.append({
                    "tool"    : "OPA",
                    "check_id": check_name,
                    "severity": "N/A",
                    "input"   : input_file,
                    "status"  : "FAIL",
                    "reason"  : (opa.get('raw_output') or 'Policy violation detected').strip()
                })
    except FileNotFoundError:
        pass
    except Exception as e:
        results.append({
            "tool"    : "OPA",
            "check_id": opa_file,
            "severity": "N/A",
            "input"   : input_file,
            "status"  : "ERROR",
            "reason"  : "Could not read OPA result: {}".format(e)
        })

# ---------------------------------------------------------------------------
# Summary + report
# ---------------------------------------------------------------------------
total   = len(results)
passed  = sum(1 for r in results if r['status'] == 'PASS')
failed  = sum(1 for r in results if r['status'] == 'FAIL')
skipped = sum(1 for r in results if r['status'] == 'SKIP')
errors  = sum(1 for r in results if r['status'] == 'ERROR')
overall = "FAIL" if (failed > 0 or errors > 0) else "PASS"

report = {
    "overall_status": overall,
    "generated_at"  : datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    "summary": {
        "total"  : total,
        "passed" : passed,
        "failed" : failed,
        "skipped": skipped,
        "errors" : errors
    },
    "results": results
}

with open('security_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Report: {} checks — {} PASS  {} FAIL  {} SKIP  {} ERROR  | Overall: {}".format(
    total, passed, failed, skipped, errors, overall))
