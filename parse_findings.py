import json
import sys

blocking = []
warnings = []

try:
    with open('tfsec_results.json', 'r') as f:
        tfsec_data = json.load(f)
    for r in (tfsec_data.get('results') or []):
        sev = (r.get('severity') or 'UNKNOWN').upper()
        loc = r.get('location') or {}
        loc_str = "{}:{}".format(loc.get('filename', ''), loc.get('start_line', ''))
        msg = "[tfsec] {} | {} | {} -- {}".format(
            r.get('rule_id', ''), sev, r.get('description', ''), loc_str)
        if sev in ('CRITICAL', 'HIGH'):
            blocking.append(msg)
        else:
            warnings.append(msg)
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
            msg = "[checkov] {} | {} | {} -- {}".format(
                c.get('check_id', ''), sev,
                check.get('name') or c.get('check_id', ''), loc_str)
            if sev in ('CRITICAL', 'HIGH'):
                blocking.append(msg)
            else:
                warnings.append(msg)
except Exception as e:
    print("WARNING: Could not parse checkov_results.json: {}".format(e))

with open('blocking.txt', 'w') as f:
    f.write('\n'.join(blocking))

with open('warnings.txt', 'w') as f:
    f.write('\n'.join(warnings))

if blocking:
    print("STATIC ANALYSIS FAILED -- {} blocking violation(s) found:".format(len(blocking)))
    for b in blocking:
        print(b)
    sys.exit(1)

print("Static analysis passed. {} advisory finding(s) noted.".format(len(warnings)))
