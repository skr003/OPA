"""
Generate a self-contained HTML dashboard from all JSON files in outputs/.
Reads: security_report.json, compliance_dashboard_*.json, *_drift.json, opa_*.json
Writes: outputs/dashboard.html
"""
import json
import os
from datetime import datetime

OUTPUTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def load_json(filename):
    path = os.path.join(OUTPUTS, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def badge(text, variant="neutral"):
    classes = {
        "pass":      "badge-pass",
        "fail":      "badge-fail",
        "error":     "badge-error",
        "skip":      "badge-skip",
        "compliant": "badge-pass",
        "drifted":   "badge-fail",
        "unknown":   "badge-skip",
        "critical":  "badge-critical",
        "high":      "badge-high",
        "medium":    "badge-medium",
        "low":       "badge-low",
        "info":      "badge-info",
    }
    cls = classes.get(str(text).lower(), "badge-neutral")
    return f'<span class="badge {cls}">{esc(text)}</span>'


# ─── Section builders ────────────────────────────────────────────────────────

def section_overview(security, dashboard):
    """Top-level KPI row shown on the Overview tab."""
    total = passed = failed = skipped = errors = 0
    overall = "N/A"
    generated = ""
    if security:
        s = security.get("summary", {})
        total, passed, failed = s.get("total",0), s.get("passed",0), s.get("failed",0)
        skipped, errors = s.get("skipped",0), s.get("errors",0)
        overall = security.get("overall_status", "N/A")
        generated = security.get("generated_at", "")

    pct = dashboard.get("overall_compliance_pct", "—") if dashboard else "—"
    comp_status = dashboard.get("overall_status", "N/A") if dashboard else "N/A"
    drifted_sc = dashboard.get("drifted_scenarios", "—") if dashboard else "—"

    ov_color = "#22c55e" if overall == "PASS" else ("#ef4444" if overall == "FAIL" else "#6b7280")
    cp_color  = "#22c55e" if pct == 100 else ("#f97316" if isinstance(pct,int) and pct >= 50 else "#ef4444")

    tool_stats = {}
    results = security.get("results", []) if security else []
    for r in results:
        t = r.get("tool","unknown")
        st = r.get("status","UNKNOWN")
        tool_stats.setdefault(t, {"PASS":0,"FAIL":0,"SKIP":0,"ERROR":0})
        tool_stats[t][st] = tool_stats[t].get(st,0) + 1

    tools      = list(tool_stats.keys())
    tool_pass  = [tool_stats[t].get("PASS",0)  for t in tools]
    tool_fail  = [tool_stats[t].get("FAIL",0)  for t in tools]
    tool_skip  = [tool_stats[t].get("SKIP",0)  for t in tools]
    tool_error = [tool_stats[t].get("ERROR",0) for t in tools]

    sev_counts = {}
    for r in results:
        sv = (r.get("severity") or "N/A").upper()
        sev_counts[sv] = sev_counts.get(sv, 0) + 1
    sev_labels = list(sev_counts.keys())
    sev_vals   = [sev_counts[k] for k in sev_labels]
    _sc = {"CRITICAL":"#7c3aed","HIGH":"#ef4444","MEDIUM":"#f97316","LOW":"#eab308","INFO":"#3b82f6","N/A":"#9ca3af"}
    sev_colors = [_sc.get(sl,"#9ca3af") for sl in sev_labels]

    sc_labels, sc_comp, sc_drift = [], [], []
    if dashboard:
        for k,v in dashboard.get("scenarios",{}).items():
            sc_labels.append(k.replace("_"," ").title())
            sc_comp.append(1 if v.get("status") == "COMPLIANT" else 0)
            sc_drift.append(1 if v.get("status") == "DRIFTED"  else 0)

    return f"""
<div class="page-title">
  <div>
    <h1>Security &amp; Compliance Overview</h1>
    <p class="subtitle">Last scan: <strong>{esc(generated or "—")}</strong></p>
  </div>
  <div style="display:flex;gap:10px;align-items:center">
    <span class="status-pill" style="background:{ov_color}20;color:{ov_color};border:1.5px solid {ov_color}">
      ● Static: {esc(overall)}
    </span>
    <span class="status-pill" style="background:{cp_color}20;color:{cp_color};border:1.5px solid {cp_color}">
      ● Drift: {esc(comp_status)}
    </span>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#dbeafe;color:#3b82f6">&#128270;</div>
    <div class="kpi-body">
      <div class="kpi-val">{total}</div>
      <div class="kpi-label">Total Checks</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#dcfce7;color:#16a34a">&#10003;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:#16a34a">{passed}</div>
      <div class="kpi-label">Passed</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#fee2e2;color:#dc2626">&#10007;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:#dc2626">{failed}</div>
      <div class="kpi-label">Failed</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#f3f4f6;color:#6b7280">&#8212;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:#6b7280">{skipped}</div>
      <div class="kpi-label">Skipped</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#ffedd5;color:#ea580c">&#9888;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:#ea580c">{errors}</div>
      <div class="kpi-label">Errors</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:{cp_color}20;color:{cp_color}">&#128737;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:{cp_color}">{pct}{'%' if pct != '—' else ''}</div>
      <div class="kpi-label">Compliance Score</div>
    </div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background:#fee2e2;color:#dc2626">&#128268;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:#dc2626">{drifted_sc}</div>
      <div class="kpi-label">Drifted Scenarios</div>
    </div>
  </div>
</div>

<div class="chart-grid three-col">
  <div class="chart-card">
    <div class="chart-card-header"><span class="chart-title">Results by Tool</span></div>
    <div class="chart-wrap"><canvas id="ov_toolChart"></canvas></div>
  </div>
  <div class="chart-card">
    <div class="chart-card-header"><span class="chart-title">Severity Breakdown</span></div>
    <div class="chart-wrap"><canvas id="ov_sevChart"></canvas></div>
  </div>
  <div class="chart-card">
    <div class="chart-card-header"><span class="chart-title">Scenario Compliance</span></div>
    <div class="chart-wrap"><canvas id="ov_scChart"></canvas></div>
  </div>
</div>

<script>
(function(){{
  new Chart(document.getElementById('ov_toolChart'),{{
    type:'bar',
    data:{{
      labels:{json.dumps(tools)},
      datasets:[
        {{label:'PASS', data:{json.dumps(tool_pass)}, backgroundColor:'#22c55e',borderRadius:4}},
        {{label:'FAIL', data:{json.dumps(tool_fail)}, backgroundColor:'#ef4444',borderRadius:4}},
        {{label:'SKIP', data:{json.dumps(tool_skip)}, backgroundColor:'#d1d5db',borderRadius:4}},
        {{label:'ERR',  data:{json.dumps(tool_error)},backgroundColor:'#f97316',borderRadius:4}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:true,
      plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}}}},
      scales:{{x:{{stacked:true,grid:{{display:false}}}},y:{{stacked:true,beginAtZero:true,grid:{{color:'#f1f5f9'}}}}}}
    }}
  }});

  new Chart(document.getElementById('ov_sevChart'),{{
    type:'doughnut',
    data:{{
      labels:{json.dumps(sev_labels)},
      datasets:[{{data:{json.dumps(sev_vals)},backgroundColor:{json.dumps(sev_colors)},borderWidth:2,borderColor:'#fff'}}]
    }},
    options:{{responsive:true,maintainAspectRatio:true,cutout:'62%',
      plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}}}}
    }}
  }});

  new Chart(document.getElementById('ov_scChart'),{{
    type:'bar',
    data:{{
      labels:{json.dumps(sc_labels)},
      datasets:[
        {{label:'Compliant',data:{json.dumps(sc_comp)}, backgroundColor:'#22c55e',borderRadius:4}},
        {{label:'Drifted',  data:{json.dumps(sc_drift)},backgroundColor:'#ef4444',borderRadius:4}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:true,indexAxis:'y',
      plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}}}},
      scales:{{x:{{stacked:true,max:1,grid:{{color:'#f1f5f9'}}}},y:{{stacked:true,grid:{{display:false}}}}}}
    }}
  }});
}})();
</script>
"""


def section_static(security):
    if not security:
        return _empty("security_report.json not found.")

    results  = security.get("results", [])
    passed   = sum(1 for r in results if r.get("status") == "PASS")
    failed   = sum(1 for r in results if r.get("status") == "FAIL")
    skipped  = sum(1 for r in results if r.get("status") == "SKIP")
    errors   = sum(1 for r in results if r.get("status") == "ERROR")
    total    = len(results)
    pct_pass = round(passed / total * 100) if total else 0

    rows = "".join(
        f"<tr>"
        f"<td><span class='tool-chip tool-{esc(r.get('tool','?').lower())}'>{esc(r.get('tool',''))}</span></td>"
        f"<td class='mono'>{esc(r.get('check_id',''))}</td>"
        f"<td>{badge(r.get('severity','N/A'))}</td>"
        f"<td class='mono dimmed'>{esc(r.get('input',''))}</td>"
        f"<td>{badge(r.get('status','UNKNOWN'))}</td>"
        f"<td class='reason'>{esc(r.get('reason',''))}</td>"
        f"</tr>"
        for r in results
    )

    return f"""
<div class="page-title">
  <h1>Static Analysis Results</h1>
  <span class="subtitle">{total} checks &nbsp;·&nbsp; {pct_pass}% pass rate</span>
</div>

<div class="progress-bar-wrap">
  <div class="progress-bar-track">
    <div class="progress-bar-fill pass"  style="width:{round(passed/total*100) if total else 0}%"></div>
    <div class="progress-bar-fill fail"  style="width:{round(failed/total*100) if total else 0}%"></div>
    <div class="progress-bar-fill skip"  style="width:{round(skipped/total*100) if total else 0}%"></div>
    <div class="progress-bar-fill error" style="width:{round(errors/total*100) if total else 0}%"></div>
  </div>
  <div class="progress-legend">
    <span class="dot pass"></span>Pass {passed}
    <span class="dot fail"></span>Fail {failed}
    <span class="dot skip"></span>Skip {skipped}
    <span class="dot error"></span>Error {errors}
  </div>
</div>

<div class="table-toolbar">
  <input class="tbl-search" data-table="staticTbl" placeholder="&#128269;  Filter checks…">
  <div class="tbl-filter-group" id="staticFilter">
    <button class="filter-btn active" data-col="4" data-val="">All</button>
    <button class="filter-btn" data-col="4" data-val="PASS">Pass</button>
    <button class="filter-btn" data-col="4" data-val="FAIL">Fail</button>
    <button class="filter-btn" data-col="4" data-val="SKIP">Skip</button>
    <button class="filter-btn" data-col="4" data-val="ERROR">Error</button>
  </div>
</div>

<div class="table-card">
  <table id="staticTbl" class="data-table sortable">
    <thead><tr>
      <th data-col="0">Tool</th>
      <th data-col="1">Check ID</th>
      <th data-col="2">Severity</th>
      <th data-col="3">Input File</th>
      <th data-col="4">Status</th>
      <th data-col="5">Reason</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""


def section_compliance(dashboard):
    if not dashboard:
        return _empty("compliance_dashboard_latest.json not found.")

    pct       = dashboard.get("overall_compliance_pct", 0)
    total     = dashboard.get("total_scenarios", 0)
    comp      = dashboard.get("compliant_scenarios", 0)
    drifted   = dashboard.get("drifted_scenarios", 0)
    total_dr  = dashboard.get("total_drifted_resources", 0)
    scenarios = dashboard.get("scenarios", {})
    phase     = dashboard.get("phase", "snapshot")

    cp_color  = "#22c55e" if pct == 100 else ("#f97316" if pct >= 50 else "#ef4444")
    remain    = 100 - pct

    sc_rows = ""
    sc_labels, sc_drifted_cnt = [], []
    for key, sc in scenarios.items():
        label  = sc.get("cis_label", key)
        status = sc.get("status", "UNKNOWN")
        dcnt   = sc.get("drifted_count", 0)
        resources = sc.get("resources", [])
        sample = ", ".join(r.get("name", r.get("id","")) for r in resources[:4]) or "—"
        sc_rows += (
            f"<tr>"
            f"<td>{esc(label)}</td>"
            f"<td>{badge(status)}</td>"
            f"<td style='text-align:center;font-weight:600'>{dcnt}</td>"
            f"<td class='dimmed mono'>{esc(sample)}</td>"
            f"</tr>"
        )
        sc_labels.append(key.replace("_"," ").title())
        sc_drifted_cnt.append(dcnt)

    return f"""
<div class="page-title">
  <h1>Compliance Dashboard</h1>
  <span class="subtitle">Phase: <strong>{esc(phase)}</strong></span>
</div>

<div class="kpi-grid">
  <div class="kpi-card" style="border-top:3px solid {cp_color}">
    <div class="kpi-icon" style="background:{cp_color}20;color:{cp_color}">&#128737;</div>
    <div class="kpi-body">
      <div class="kpi-val" style="color:{cp_color}">{pct}%</div>
      <div class="kpi-label">Compliance Score</div>
    </div>
  </div>
  <div class="kpi-card" style="border-top:3px solid #22c55e">
    <div class="kpi-icon" style="background:#dcfce7;color:#16a34a">&#10003;</div>
    <div class="kpi-body"><div class="kpi-val" style="color:#16a34a">{comp}/{total}</div><div class="kpi-label">Compliant Scenarios</div></div>
  </div>
  <div class="kpi-card" style="border-top:3px solid #ef4444">
    <div class="kpi-icon" style="background:#fee2e2;color:#dc2626">&#128268;</div>
    <div class="kpi-body"><div class="kpi-val" style="color:#dc2626">{drifted}</div><div class="kpi-label">Drifted Scenarios</div></div>
  </div>
  <div class="kpi-card" style="border-top:3px solid #f97316">
    <div class="kpi-icon" style="background:#ffedd5;color:#ea580c">&#9888;</div>
    <div class="kpi-body"><div class="kpi-val" style="color:#ea580c">{total_dr}</div><div class="kpi-label">Drifted Resources</div></div>
  </div>
</div>

<div class="chart-grid two-col">
  <div class="chart-card">
    <div class="chart-card-header"><span class="chart-title">Compliance Gauge</span></div>
    <div class="chart-wrap gauge-wrap">
      <canvas id="gaugeChart"></canvas>
      <div class="gauge-label" style="color:{cp_color}">{pct}%</div>
    </div>
  </div>
  <div class="chart-card">
    <div class="chart-card-header"><span class="chart-title">Drifted Resources per Scenario</span></div>
    <div class="chart-wrap"><canvas id="scDriftChart"></canvas></div>
  </div>
</div>

<script>
(function(){{
  new Chart(document.getElementById('gaugeChart'),{{
    type:'doughnut',
    data:{{
      labels:['Compliant','Non-Compliant'],
      datasets:[{{
        data:[{pct},{remain}],
        backgroundColor:['{cp_color}','#f1f5f9'],
        borderWidth:0,
        circumference:220,
        rotation:250
      }}]
    }},
    options:{{responsive:true,maintainAspectRatio:true,cutout:'78%',
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:function(c){{return c.label+': '+c.raw+'%';}}}}}}}}
    }}
  }});

  new Chart(document.getElementById('scDriftChart'),{{
    type:'bar',
    data:{{
      labels:{json.dumps(sc_labels)},
      datasets:[{{
        label:'Drifted Resources',
        data:{json.dumps(sc_drifted_cnt)},
        backgroundColor:{json.dumps(['#ef4444' if v > 0 else '#22c55e' for v in sc_drifted_cnt])},
        borderRadius:6
      }}]
    }},
    options:{{responsive:true,maintainAspectRatio:true,
      plugins:{{legend:{{display:false}}}},
      scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}},grid:{{color:'#f1f5f9'}}}},x:{{grid:{{display:false}}}}}}
    }}
  }});
}})();
</script>

<div class="table-card">
  <table class="data-table">
    <thead><tr>
      <th>CIS / Governance Control</th>
      <th>Status</th>
      <th style="text-align:center">Drifted Resources</th>
      <th>Sample Affected Resources</th>
    </tr></thead>
    <tbody>{sc_rows}</tbody>
  </table>
</div>
"""


def section_drift(drift_files):
    if not any(drift_files.values()):
        return _empty("No drift JSON files found in outputs/.")

    chart_labels, chart_vals, chart_colors = [], [], []
    tables_html = ""

    for name, data in drift_files.items():
        if not data:
            continue
        drifted  = data.get("drifted", False)
        resources = data.get("resources", [])
        label    = name.replace("_drift","").replace("_"," ").title()
        status   = "DRIFTED" if drifted else "COMPLIANT"

        chart_labels.append(label)
        chart_vals.append(data.get("drifted_count", 0))
        chart_colors.append("#ef4444" if drifted else "#22c55e")

        if resources:
            keys   = list(resources[0].keys())
            header = "".join(f"<th>{esc(k)}</th>" for k in keys)
            trows  = "".join(
                "<tr>" + "".join(f"<td class='mono' style='font-size:12px'>{esc(str(r.get(k,'')))}</td>" for k in keys) + "</tr>"
                for r in resources
            )
            table = f"<table class='data-table'><thead><tr>{header}</tr></thead><tbody>{trows}</tbody></table>"
        else:
            table = "<p class='empty-msg'>No resources recorded.</p>"

        tables_html += f"""
<div class="drift-block">
  <div class="drift-block-header">
    <span class="drift-block-title">{esc(label)}</span>
    {badge(status)}
  </div>
  <div class="table-card" style="margin-top:0;border-radius:0 0 10px 10px">{table}</div>
</div>
"""

    return f"""
<div class="page-title">
  <h1>Drift Detection</h1>
  <span class="subtitle">Live infrastructure vs IaC baseline</span>
</div>

<div class="chart-grid one-col-center">
  <div class="chart-card" style="max-width:560px">
    <div class="chart-card-header"><span class="chart-title">Drifted Resources by Scenario</span></div>
    <div class="chart-wrap"><canvas id="driftBar"></canvas></div>
  </div>
</div>

<script>
(function(){{
  new Chart(document.getElementById('driftBar'),{{
    type:'bar',
    data:{{
      labels:{json.dumps(chart_labels)},
      datasets:[{{
        label:'Drifted Resources',
        data:{json.dumps(chart_vals)},
        backgroundColor:{json.dumps(chart_colors)},
        borderRadius:6
      }}]
    }},
    options:{{responsive:true,maintainAspectRatio:true,
      plugins:{{legend:{{display:false}}}},
      scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}},grid:{{color:'#f1f5f9'}}}},x:{{grid:{{display:false}}}}}}
    }}
  }});
}})();
</script>

{tables_html}
"""


def section_opa(opa_files):
    parts = []
    statuses, labels = [], []
    for fname, data in opa_files.items():
        if not data:
            continue
        check  = data.get("check", fname)
        status = data.get("status", "UNKNOWN")
        policy = data.get("policy", "")
        viols  = data.get("violations", [])
        labels.append(check)
        statuses.append(status)

        viol_html = (
            "<ul class='viol-list'>" +
            "".join(f"<li>{esc(v)}</li>" for v in viols) +
            "</ul>"
        ) if viols else "<p class='empty-msg' style='color:#16a34a'>&#10003; No violations detected.</p>"

        parts.append(f"""
<div class="opa-card {'opa-fail' if 'FAIL' in status.upper() or 'FAILED' in status.upper() else 'opa-pass'}">
  <div class="opa-card-header">
    <div>
      <div class="opa-check-name">{esc(check)}</div>
      <div class="opa-policy">{esc(policy)}</div>
    </div>
    {badge(status)}
  </div>
  <div class="opa-body">{viol_html}</div>
</div>
""")

    if not parts:
        return _empty("No OPA result files found in outputs/.")

    pass_count = sum(1 for s in statuses if "PASS" in s.upper())
    fail_count = len(statuses) - pass_count

    return f"""
<div class="page-title">
  <h1>OPA Policy Results</h1>
  <span class="subtitle">{len(statuses)} policies evaluated &nbsp;·&nbsp; {pass_count} passed &nbsp;·&nbsp; {fail_count} failed</span>
</div>

<div class="chart-grid one-col-center">
  <div class="chart-card" style="max-width:360px">
    <div class="chart-card-header"><span class="chart-title">Policy Outcomes</span></div>
    <div class="chart-wrap"><canvas id="opaChart"></canvas></div>
  </div>
</div>

<script>
(function(){{
  new Chart(document.getElementById('opaChart'),{{
    type:'pie',
    data:{{
      labels:['Passed','Failed'],
      datasets:[{{data:[{pass_count},{fail_count}],backgroundColor:['#22c55e','#ef4444'],borderWidth:2,borderColor:'#fff'}}]
    }},
    options:{{responsive:true,maintainAspectRatio:true,
      plugins:{{legend:{{position:'bottom',labels:{{boxWidth:14,font:{{size:12}}}}}}}}
    }}
  }});
}})();
</script>

{''.join(parts)}
"""


def _empty(msg):
    return f"<div class='empty-state'><div class='empty-icon'>&#128203;</div><p>{esc(msg)}</p></div>"


# ─── CSS ─────────────────────────────────────────────────────────────────────

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --sidebar-w: 230px;
  --header-h:  56px;
  --bg:        #f0f4f8;
  --surface:   #ffffff;
  --border:    #e2e8f0;
  --text:      #1e293b;
  --muted:     #64748b;
  --accent:    #3b82f6;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── Top header ── */
.top-header {
  position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
  background: #0f172a;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
}
.top-header .brand {
  display: flex; align-items: center; gap: 10px;
  color: #fff; font-size: 16px; font-weight: 700; letter-spacing: .3px;
}
.top-header .brand span { font-size: 20px; }
.top-header .meta { color: #94a3b8; font-size: 12px; }

/* ── Sidebar ── */
.sidebar {
  position: fixed; top: var(--header-h); left: 0; bottom: 0;
  width: var(--sidebar-w);
  background: #1e293b;
  padding: 20px 0;
  overflow-y: auto;
  z-index: 90;
}
.sidebar-section { padding: 6px 16px 4px; color: #475569; font-size: 10px;
                   font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 20px;
  color: #94a3b8; font-size: 13.5px; font-weight: 500;
  cursor: pointer; border-left: 3px solid transparent;
  transition: all .15s;
  user-select: none;
}
.nav-item:hover { background: #334155; color: #e2e8f0; }
.nav-item.active { background: #1d4ed820; color: #60a5fa;
                   border-left-color: #3b82f6; }
.nav-item .nav-icon { font-size: 16px; width: 20px; text-align: center; }

/* ── Main content ── */
.main {
  margin-left: var(--sidebar-w);
  margin-top: var(--header-h);
  padding: 28px 32px;
  min-height: calc(100vh - var(--header-h));
}
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* ── Page title ── */
.page-title {
  display: flex; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; gap: 10px;
  margin-bottom: 24px;
}
.page-title h1 { font-size: 22px; font-weight: 800; color: #0f172a; }
.subtitle { font-size: 13px; color: var(--muted); margin-top: 3px; display: block; }

/* ── KPI grid ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 26px;
}
.kpi-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 18px 16px;
  display: flex; align-items: center; gap: 14px;
  border-top: 3px solid #e2e8f0;
  transition: box-shadow .2s;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); }
.kpi-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.kpi-val { font-size: 26px; font-weight: 800; line-height: 1; color: #0f172a; }
.kpi-label { font-size: 11px; color: var(--muted); margin-top: 4px;
             text-transform: uppercase; letter-spacing: .5px; }

/* ── Status pill ── */
.status-pill {
  padding: 5px 14px; border-radius: 20px;
  font-size: 12px; font-weight: 600;
}

/* ── Chart grid ── */
.chart-grid { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 26px; }
.chart-grid.three-col .chart-card { flex: 1; min-width: 220px; }
.chart-grid.two-col   .chart-card { flex: 1; min-width: 260px; }
.chart-grid.one-col-center { justify-content: center; }

.chart-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
}
.chart-card-header {
  padding: 14px 18px 0;
  border-bottom: 0;
}
.chart-title { font-size: 13px; font-weight: 600; color: #374151; }
.chart-wrap { padding: 14px 18px 18px; }
.gauge-wrap { position: relative; display: flex; align-items: center; justify-content: center; }
.gauge-label {
  position: absolute; bottom: 32px;
  font-size: 26px; font-weight: 800;
}

/* ── Progress bar ── */
.progress-bar-wrap { margin-bottom: 20px; }
.progress-bar-track {
  display: flex; height: 10px; border-radius: 99px; overflow: hidden; background: #f1f5f9;
}
.progress-bar-fill { height: 100%; transition: width .4s; }
.progress-bar-fill.pass  { background: #22c55e; }
.progress-bar-fill.fail  { background: #ef4444; }
.progress-bar-fill.skip  { background: #d1d5db; }
.progress-bar-fill.error { background: #f97316; }
.progress-legend {
  display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--muted);
}
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
.dot.pass  { background: #22c55e; }
.dot.fail  { background: #ef4444; }
.dot.skip  { background: #d1d5db; }
.dot.error { background: #f97316; }

/* ── Table toolbar ── */
.table-toolbar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-bottom: 12px;
}
.tbl-search {
  flex: 1; min-width: 200px; max-width: 340px;
  padding: 8px 14px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 13px; outline: none; background: var(--surface);
}
.tbl-search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px #3b82f620; }
.tbl-filter-group { display: flex; gap: 6px; flex-wrap: wrap; }
.filter-btn {
  padding: 6px 14px; border-radius: 20px; border: 1.5px solid var(--border);
  font-size: 12px; font-weight: 500; cursor: pointer; background: var(--surface);
  color: var(--muted); transition: all .15s;
}
.filter-btn:hover, .filter-btn.active {
  border-color: var(--accent); color: var(--accent); background: #3b82f610;
}

/* ── Data table ── */
.table-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden; margin-bottom: 24px;
}
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table thead tr { background: #f8fafc; }
.data-table th {
  padding: 11px 14px; text-align: left; font-weight: 600; color: #374151;
  font-size: 11px; text-transform: uppercase; letter-spacing: .5px;
  border-bottom: 1px solid var(--border); white-space: nowrap;
  cursor: pointer; user-select: none;
}
.data-table th:hover { background: #f1f5f9; }
.data-table th.sort-asc::after  { content: ' ↑'; color: var(--accent); }
.data-table th.sort-desc::after { content: ' ↓'; color: var(--accent); }
.data-table td {
  padding: 10px 14px; border-bottom: 1px solid #f1f5f9; vertical-align: top;
}
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: #f8fafc; }
.mono { font-family: 'Cascadia Code','Fira Code','Consolas',monospace; font-size: 12px; }
.dimmed { color: var(--muted); }
.reason { max-width: 340px; word-break: break-word; color: #374151; }

/* ── Tool chips ── */
.tool-chip {
  padding: 2px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .4px;
}
.tool-tfsec   { background:#dbeafe; color:#1d4ed8; }
.tool-checkov { background:#ede9fe; color:#6d28d9; }
.tool-opa     { background:#fef9c3; color:#854d0e; }

/* ── Badges ── */
.badge {
  padding: 2px 10px; border-radius: 12px;
  font-size: 11px; font-weight: 700; white-space: nowrap; display: inline-block;
}
.badge-pass      { background:#dcfce7; color:#15803d; }
.badge-fail      { background:#fee2e2; color:#b91c1c; }
.badge-error     { background:#ffedd5; color:#c2410c; }
.badge-skip      { background:#f3f4f6; color:#4b5563; }
.badge-neutral   { background:#f3f4f6; color:#4b5563; }
.badge-critical  { background:#ede9fe; color:#6d28d9; }
.badge-high      { background:#fee2e2; color:#b91c1c; }
.badge-medium    { background:#ffedd5; color:#c2410c; }
.badge-low       { background:#fef9c3; color:#854d0e; }
.badge-info      { background:#dbeafe; color:#1d4ed8; }

/* ── OPA cards ── */
.opa-card {
  border: 1px solid var(--border); border-radius: 12px;
  margin-bottom: 16px; overflow: hidden;
}
.opa-card.opa-fail { border-left: 4px solid #ef4444; }
.opa-card.opa-pass { border-left: 4px solid #22c55e; }
.opa-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; background: var(--surface);
}
.opa-check-name { font-weight: 700; font-size: 14px; color: #0f172a; }
.opa-policy { font-size: 11px; color: var(--muted); margin-top: 2px; font-family: monospace; }
.opa-body { padding: 14px 18px; background: #fafafa; border-top: 1px solid var(--border); }
.viol-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.viol-list li {
  background: #fee2e2; color: #b91c1c; padding: 7px 12px;
  border-radius: 6px; font-size: 12px; font-family: monospace; word-break: break-word;
}

/* ── Drift blocks ── */
.drift-block { margin-bottom: 24px; }
.drift-block-header {
  display: flex; align-items: center; gap: 12px;
  background: #1e293b; padding: 12px 18px;
  border-radius: 10px 10px 0 0;
}
.drift-block-title { font-weight: 700; font-size: 14px; color: #e2e8f0; }

/* ── Empty states ── */
.empty-state {
  text-align: center; padding: 60px 20px; color: var(--muted);
}
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.empty-msg { color: var(--muted); font-size: 13px; margin: 6px 0; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .main { margin-left: 0; padding: 16px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
"""


# ─── JS ──────────────────────────────────────────────────────────────────────

JS = """
// Tab navigation
function showTab(id, el) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}

// Per-table search
document.querySelectorAll('.tbl-search').forEach(function(inp) {
  inp.addEventListener('input', function() {
    var tblId = this.dataset.table;
    var q = this.value.toLowerCase();
    document.querySelectorAll('#' + tblId + ' tbody tr').forEach(function(r) {
      r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
});

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var group = this.closest('.tbl-filter-group');
    group.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    var col = parseInt(this.dataset.col);
    var val = this.dataset.val.toLowerCase();
    var tbl = this.closest('section, .tab-pane').querySelector('tbody');
    if (!tbl) return;
    tbl.querySelectorAll('tr').forEach(function(r) {
      if (!val) { r.style.display = ''; return; }
      var cell = r.cells[col];
      r.style.display = (cell && cell.textContent.trim().toLowerCase() === val) ? '' : 'none';
    });
  });
});

// Sortable tables
document.querySelectorAll('table.sortable th').forEach(function(th) {
  th.addEventListener('click', function() {
    var table = this.closest('table');
    var col   = Array.from(this.parentNode.children).indexOf(this);
    var asc   = !this.classList.contains('sort-asc');
    table.querySelectorAll('th').forEach(t => t.classList.remove('sort-asc','sort-desc'));
    this.classList.add(asc ? 'sort-asc' : 'sort-desc');
    var tbody = table.querySelector('tbody');
    Array.from(tbody.querySelectorAll('tr'))
      .sort(function(a, b) {
        var at = (a.cells[col]||{}).textContent||'';
        var bt = (b.cells[col]||{}).textContent||'';
        return asc ? at.localeCompare(bt, undefined, {numeric:true})
                   : bt.localeCompare(at, undefined, {numeric:true});
      })
      .forEach(r => tbody.appendChild(r));
  });
});
"""


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    security  = load_json("security_report.json")
    dashboard = load_json("compliance_dashboard_latest.json")
    drift_files = {
        "nsg_drift":     load_json("nsg_drift.json"),
        "storage_drift": load_json("storage_drift.json"),
        "scaling_drift": load_json("scaling_drift.json"),
        "iam_drift":     load_json("iam_drift.json"),
    }
    opa_files = {
        "CIS Azure Benchmark": load_json("opa_cis_result.json"),
        "VM Size Policy":      load_json("opa_vm_result.json"),
        "Mandatory Tags":      load_json("opa_tags_result.json"),
    }

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CSPM Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>

<!-- Top header -->
<header class="top-header">
  <div class="brand">
    <span>&#128737;</span>
    CSPM Security Dashboard
  </div>
  <span class="meta">Generated: {now}</span>
</header>

<!-- Sidebar -->
<nav class="sidebar">
  <div class="sidebar-section">Navigation</div>
  <div class="nav-item active" onclick="showTab('tab-overview',this)">
    <span class="nav-icon">&#127968;</span> Overview
  </div>
  <div class="nav-item" onclick="showTab('tab-static',this)">
    <span class="nav-icon">&#128270;</span> Static Analysis
  </div>
  <div class="nav-item" onclick="showTab('tab-compliance',this)">
    <span class="nav-icon">&#128737;</span> Compliance
  </div>
  <div class="nav-item" onclick="showTab('tab-drift',this)">
    <span class="nav-icon">&#128268;</span> Drift Detection
  </div>
  <div class="nav-item" onclick="showTab('tab-opa',this)">
    <span class="nav-icon">&#128203;</span> OPA Policies
  </div>
</nav>

<!-- Main -->
<main class="main">
  <div id="tab-overview"   class="tab-pane active">{section_overview(security, dashboard)}</div>
  <div id="tab-static"     class="tab-pane">{section_static(security)}</div>
  <div id="tab-compliance" class="tab-pane">{section_compliance(dashboard)}</div>
  <div id="tab-drift"      class="tab-pane">{section_drift(drift_files)}</div>
  <div id="tab-opa"        class="tab-pane">{section_opa(opa_files)}</div>
</main>

<script>{JS}</script>
</body>
</html>
"""

    out = os.path.join(OUTPUTS, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Dashboard UI] Written to {out}")


if __name__ == "__main__":
    main()
