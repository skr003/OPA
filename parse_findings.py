import json
import sys

blocking = []
warnings = []

def make_entry(tool, rule_id, severity, description, location):
    return {
        "tool": tool,
        "rule_id": rule_id,
        "severity": severity,
        "description": description,
        "location": location,
        "message": "[{}] {} | {} | {} -- {}".format(
            tool, rule_id, severity, description, location)
    }

try:
    with open('tfsec_results.json', 'r') as f:
        tfsec_data = json.load(f)
    for r in (tfsec_data.get('results') or []):
        sev = (r.get('severity') or 'UNKNOWN').upper()
        loc = r.get('location') or {}
        loc_str = "{}:{}".format(loc.get('filename', ''), loc.get('start_line', ''))
        entry = make_entry('tfsec', r.get('rule_id', ''), sev, r.get('description', ''), loc_str)
        if sev in ('CRITICAL', 'HIGH'):
            blocking.append(entry)
        else:
            warnings.append(entry)
except Exception as e:
    print("WARNING: Could not parse tfsec_results.json: {}".format(e))

try:
    with open('checkov_results.json', 'r') as f:
        raw = f.read()
    json_start = raw.find('{')
    if json_start >= 0:
        checkov_data = json.loads(raw[json_start:])
        results = checkov_data.get('results') or {}
        for c in (results.get('failed_checks') or []):
            check = c.get('check') or {}
            sev = (c.get('severity') or check.get('severity') or 'MEDIUM').upper()
            file_line = c.get('file_line_range') or [0]
            loc_str = "{}:{}".format(c.get('repo_file_path', ''), file_line[0])
            desc = check.get('name') or c.get('check_id', '')
            entry = make_entry('checkov', c.get('check_id', ''), sev, desc, loc_str)
            if sev in ('CRITICAL', 'HIGH'):
                blocking.append(entry)
            else:
                warnings.append(entry)
except Exception as e:
    print("WARNING: Could not parse checkov_results.json: {}".format(e))

# Per-tool summary
tool_stats = {}
for e in blocking + warnings:
    t = e['tool']
    if t not in tool_stats:
        tool_stats[t] = {'blocking': 0, 'warnings': 0}
for e in blocking:
    tool_stats[e['tool']]['blocking'] += 1
for e in warnings:
    tool_stats[e['tool']]['warnings'] += 1

findings = {
    "summary": {
        "status": "FAILED" if blocking else "PASSED",
        "total_blocking": len(blocking),
        "total_warnings": len(warnings),
        "by_tool": tool_stats
    },
    "blocking": blocking,
    "warnings": warnings
}

with open('findings.json', 'w') as f:
    json.dump(findings, f, indent=2)

with open('blocking.txt', 'w') as f:
    f.write('\n'.join(e['message'] for e in blocking))

with open('warnings.txt', 'w') as f:
    f.write('\n'.join(e['message'] for e in warnings))

if blocking:
    print("STATIC ANALYSIS FAILED -- {} blocking violation(s) found:".format(len(blocking)))
    for b in blocking:
        print(b['message'])
    sys.exit(1)

print("Static analysis passed. {} advisory finding(s) noted.".format(len(warnings)))
sys.exit(0)
