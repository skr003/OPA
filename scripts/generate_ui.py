"""
Generate a self-contained HTML dashboard from all JSON files in outputs/.
Reads: security_report.json, compliance_dashboard_*.json, *_drift.json, opa_*.json
Writes: outputs/dashboard.html
"""
import json
import os
import sys
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


def status_badge(status):
    colors = {
        "PASS": ("#22c55e", "#dcfce7"),
        "FAIL": ("#ef4444", "#fee2e2"),
        "ERROR": ("#f97316", "#ffedd5"),
        "SKIP": ("#6b7280", "#f3f4f6"),
        "COMPLIANT": ("#22c55e", "#dcfce7"),
        "DRIFTED": ("#ef4444", "#fee2e2"),
        "UNKNOWN": ("#6b7280", "#f3f4f6"),
    }
    fg, bg = colors.get(status.upper(), ("#6b7280", "#f3f4f6"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:12px;font-size:12px;font-weight:600;">{status}</span>')


def sev_badge(sev):
    colors = {
        "CRITICAL": ("#7c3aed", "#ede9fe"),
        "HIGH": ("#ef4444", "#fee2e2"),
        "MEDIUM": ("#f97316", "#ffedd5"),
        "LOW": ("#eab308", "#fef9c3"),
        "INFO": ("#3b82f6", "#dbeafe"),
    }
    fg, bg = colors.get((sev or "").upper(), ("#6b7280", "#f3f4f6"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:10px;font-size:11px;font-weight:600;">{sev or "N/A"}</span>')


def escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_security_section(report):
    if not report:
        return "<p style='color:#6b7280'>security_report.json not found.</p>"

    summary = report.get("summary", {})
    results = report.get("results", [])
    overall = report.get("overall_status", "UNKNOWN")
    generated = report.get("generated_at", "")

    total   = summary.get("total", 0)
    passed  = summary.get("passed", 0)
    failed  = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    errors  = summary.get("errors", 0)

    # per-tool counts for chart
    tool_stats = {}
    for r in results:
        t = r.get("tool", "unknown")
        s = r.get("status", "UNKNOWN")
        tool_stats.setdefault(t, {"PASS": 0, "FAIL": 0, "SKIP": 0, "ERROR": 0})
        tool_stats[t][s] = tool_stats[t].get(s, 0) + 1

    sev_counts = {}
    for r in results:
        sv = (r.get("severity") or "N/A").upper()
        sev_counts[sv] = sev_counts.get(sv, 0) + 1

    tools = list(tool_stats.keys())
    tool_pass  = [tool_stats[t].get("PASS", 0)  for t in tools]
    tool_fail  = [tool_stats[t].get("FAIL", 0)  for t in tools]
    tool_skip  = [tool_stats[t].get("SKIP", 0)  for t in tools]
    tool_error = [tool_stats[t].get("ERROR", 0) for t in tools]

    sev_labels = list(sev_counts.keys())
    sev_vals   = [sev_counts[k] for k in sev_labels]
    sev_colors = []
    _sc = {"CRITICAL":"#7c3aed","HIGH":"#ef4444","MEDIUM":"#f97316","LOW":"#eab308","INFO":"#3b82f6","N/A":"#9ca3af"}
    for sl in sev_labels:
        sev_colors.append(_sc.get(sl, "#9ca3af"))

    rows = ""
    for r in results:
        rows += (
            f"<tr>"
            f"<td>{escape(r.get('tool',''))}</td>"
            f"<td style='font-family:monospace;font-size:12px'>{escape(r.get('check_id',''))}</td>"
            f"<td>{sev_badge(r.get('severity',''))}</td>"
            f"<td style='font-size:12px;color:#6b7280'>{escape(r.get('input',''))}</td>"
            f"<td>{status_badge(r.get('status','UNKNOWN'))}</td>"
            f"<td style='font-size:12px;max-width:320px;word-break:break-word'>{escape(r.get('reason',''))}</td>"
            f"</tr>"
        )

    return f"""
<div class="section-header">
  <h2>Static Analysis &amp; Policy Results</h2>
  <span style="color:#6b7280;font-size:13px">Generated: {escape(generated)} &nbsp;|&nbsp; Overall: {status_badge(overall)}</span>
</div>

<!-- Summary cards -->
<div class="card-row">
  <div class="card"><div class="card-num">{total}</div><div class="card-label">Total Checks</div></div>
  <div class="card pass"><div class="card-num">{passed}</div><div class="card-label">Passed</div></div>
  <div class="card fail"><div class="card-num">{failed}</div><div class="card-label">Failed</div></div>
  <div class="card skip"><div class="card-num">{skipped}</div><div class="card-label">Skipped</div></div>
  <div class="card error"><div class="card-num">{errors}</div><div class="card-label">Errors</div></div>
</div>

<!-- Charts -->
<div class="chart-row">
  <div class="chart-box">
    <h3>Results by Tool</h3>
    <canvas id="toolChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>Severity Distribution</h3>
    <canvas id="sevChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>Overall Pass / Fail</h3>
    <canvas id="overallChart"></canvas>
  </div>
</div>

<script>
(function(){{
  var tctx = document.getElementById('toolChart').getContext('2d');
  new Chart(tctx, {{
    type: 'bar',
    data: {{
      labels: {json.dumps(tools)},
      datasets: [
        {{label:'PASS',  data:{json.dumps(tool_pass)},  backgroundColor:'#22c55e'}},
        {{label:'FAIL',  data:{json.dumps(tool_fail)},  backgroundColor:'#ef4444'}},
        {{label:'SKIP',  data:{json.dumps(tool_skip)},  backgroundColor:'#9ca3af'}},
        {{label:'ERROR', data:{json.dumps(tool_error)}, backgroundColor:'#f97316'}}
      ]
    }},
    options:{{ responsive:true, plugins:{{legend:{{position:'bottom'}}}}, scales:{{x:{{stacked:true}},y:{{stacked:true,beginAtZero:true}}}} }}
  }});

  var sctx = document.getElementById('sevChart').getContext('2d');
  new Chart(sctx, {{
    type: 'doughnut',
    data: {{
      labels: {json.dumps(sev_labels)},
      datasets: [{{ data:{json.dumps(sev_vals)}, backgroundColor:{json.dumps(sev_colors)} }}]
    }},
    options:{{ responsive:true, plugins:{{legend:{{position:'bottom'}}}} }}
  }});

  var octx = document.getElementById('overallChart').getContext('2d');
  new Chart(octx, {{
    type: 'pie',
    data: {{
      labels: ['PASS','FAIL','SKIP','ERROR'],
      datasets: [{{ data:[{passed},{failed},{skipped},{errors}], backgroundColor:['#22c55e','#ef4444','#9ca3af','#f97316'] }}]
    }},
    options:{{ responsive:true, plugins:{{legend:{{position:'bottom'}}}} }}
  }});
}})();
</script>

<!-- Table -->
<div class="table-wrap">
  <table>
    <thead><tr>
      <th>Tool</th><th>Check ID</th><th>Severity</th><th>Input File</th><th>Status</th><th>Reason</th>
    </tr></thead>
    <tbody id="secBody">{rows}</tbody>
  </table>
</div>

<script>
(function(){{
  var rows = document.querySelectorAll('#secBody tr');
  var search = document.getElementById('globalSearch');
  if (search) {{
    search.addEventListener('input', function(){{
      var q = this.value.toLowerCase();
      rows.forEach(function(r){{ r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; }});
    }});
  }}
}})();
</script>
"""


def build_compliance_section(dashboard):
    if not dashboard:
        return "<p style='color:#6b7280'>compliance_dashboard_latest.json not found.</p>"

    phase   = dashboard.get("phase", "")
    pct     = dashboard.get("overall_compliance_pct", 0)
    overall = dashboard.get("overall_status", "UNKNOWN")
    total   = dashboard.get("total_scenarios", 0)
    comp    = dashboard.get("compliant_scenarios", 0)
    drifted = dashboard.get("drifted_scenarios", 0)
    total_dr= dashboard.get("total_drifted_resources", 0)
    scenarios = dashboard.get("scenarios", {})

    rows = ""
    sc_labels, sc_compliant, sc_drifted = [], [], []
    for key, sc in scenarios.items():
        label  = sc.get("cis_label", key)
        status = sc.get("status", "UNKNOWN")
        dcnt   = sc.get("drifted_count", 0)
        resources = sc.get("resources", [])
        res_str = ", ".join(
            r.get("name", r.get("id", "")) for r in resources[:5]
        ) if resources else "—"
        rows += (
            f"<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{status_badge(status)}</td>"
            f"<td style='text-align:center'>{dcnt}</td>"
            f"<td style='font-size:12px;color:#6b7280'>{escape(res_str)}</td>"
            f"</tr>"
        )
        sc_labels.append(key.replace("_", " ").title())
        sc_compliant.append(1 if status == "COMPLIANT" else 0)
        sc_drifted.append(1 if status == "DRIFTED" else 0)

    pct_color = "#22c55e" if pct == 100 else ("#f97316" if pct >= 50 else "#ef4444")

    return f"""
<div class="section-header">
  <h2>Compliance Dashboard <span style="font-size:14px;color:#6b7280">({escape(phase)})</span></h2>
</div>

<div class="card-row">
  <div class="card" style="border-top:4px solid {pct_color}">
    <div class="card-num" style="color:{pct_color}">{pct}%</div>
    <div class="card-label">Compliance Score</div>
  </div>
  <div class="card pass"><div class="card-num">{comp}</div><div class="card-label">Compliant Scenarios</div></div>
  <div class="card fail"><div class="card-num">{drifted}</div><div class="card-label">Drifted Scenarios</div></div>
  <div class="card error"><div class="card-num">{total_dr}</div><div class="card-label">Drifted Resources</div></div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h3>Scenario Compliance Status</h3>
    <canvas id="scChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>Compliance Score</h3>
    <canvas id="gaugeChart"></canvas>
  </div>
</div>

<script>
(function(){{
  var ctx = document.getElementById('scChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {json.dumps(sc_labels)},
      datasets: [
        {{label:'Compliant', data:{json.dumps(sc_compliant)}, backgroundColor:'#22c55e'}},
        {{label:'Drifted',   data:{json.dumps(sc_drifted)},   backgroundColor:'#ef4444'}}
      ]
    }},
    options:{{ responsive:true, indexAxis:'y', plugins:{{legend:{{position:'bottom'}}}}, scales:{{x:{{stacked:true,max:1}},y:{{stacked:true}}}} }}
  }});

  var gctx = document.getElementById('gaugeChart').getContext('2d');
  new Chart(gctx, {{
    type: 'doughnut',
    data: {{
      labels: ['Compliant','Non-Compliant'],
      datasets: [{{ data:[{pct},{100-pct}], backgroundColor:['{pct_color}','#e5e7eb'], circumference:180, rotation:270 }}]
    }},
    options:{{
      responsive:true, cutout:'75%',
      plugins:{{
        legend:{{display:false}},
        tooltip:{{callbacks:{{label:function(c){{return c.label+': '+c.raw+'%';}}}}}}
      }}
    }}
  }});
}})();
</script>

<div class="table-wrap">
  <table>
    <thead><tr><th>CIS Control</th><th>Status</th><th>Drifted Resources</th><th>Sample Resources</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""


def build_drift_section(drift_files):
    if not any(drift_files.values()):
        return "<p style='color:#6b7280'>No drift files found in outputs/.</p>"

    html = ""
    for name, data in drift_files.items():
        if not data:
            continue
        drifted = data.get("drifted", False)
        resources = data.get("resources", [])
        label = name.replace("_drift", "").replace("_", " ").title()
        status_str = "DRIFTED" if drifted else "COMPLIANT"

        rows = ""
        if resources:
            sample = resources[0]
            keys = list(sample.keys())
            header = "".join(f"<th>{escape(k)}</th>" for k in keys)
            for res in resources:
                cells = "".join(
                    f"<td style='font-size:12px'>{escape(str(res.get(k,'')))}</td>"
                    for k in keys
                )
                rows += f"<tr>{cells}</tr>"
            rows = f"<thead><tr>{header}</tr></thead><tbody>{rows}</tbody>"
        else:
            rows = "<tbody><tr><td colspan='4' style='color:#6b7280'>No resources found.</td></tr></tbody>"

        html += f"""
<div style="margin-bottom:28px">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
    <h3 style="margin:0">{escape(label)}</h3>
    {status_badge(status_str)}
  </div>
  <div class="table-wrap">
    <table>{rows}</table>
  </div>
</div>
"""

    # Bar chart: drifted count per scenario
    chart_labels = []
    chart_vals   = []
    chart_colors = []
    for name, data in drift_files.items():
        if not data:
            continue
        chart_labels.append(name.replace("_drift", "").replace("_", " ").title())
        chart_vals.append(data.get("drifted_count", 0))
        chart_colors.append("#ef4444" if data.get("drifted") else "#22c55e")

    return f"""
<div class="section-header"><h2>Drift Detection Details</h2></div>
<div class="chart-row">
  <div class="chart-box" style="max-width:500px">
    <h3>Drifted Resource Count by Scenario</h3>
    <canvas id="driftChart"></canvas>
  </div>
</div>
<script>
(function(){{
  var ctx = document.getElementById('driftChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {json.dumps(chart_labels)},
      datasets: [{{ label:'Drifted Resources', data:{json.dumps(chart_vals)}, backgroundColor:{json.dumps(chart_colors)} }}]
    }},
    options:{{ responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}} }}
  }});
}})();
</script>
{html}
"""


def build_opa_section(opa_files):
    parts = []
    for fname, data in opa_files.items():
        if not data:
            continue
        check  = data.get("check", fname)
        status = data.get("status", "UNKNOWN")
        policy = data.get("policy", "")
        viols  = data.get("violations", [])

        viol_html = ""
        if viols:
            items = "".join(f"<li style='font-size:12px;margin:3px 0'>{escape(v)}</li>" for v in viols)
            viol_html = f"<ul style='margin:8px 0 0 16px;padding:0;color:#ef4444'>{items}</ul>"
        else:
            viol_html = "<p style='color:#22c55e;margin:6px 0'>No violations.</p>"

        parts.append(f"""
<div style="border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:16px">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
    <strong>{escape(check)}</strong>
    {status_badge(status)}
    <span style="color:#9ca3af;font-size:12px">{escape(policy)}</span>
  </div>
  {viol_html}
</div>
""")

    if not parts:
        return "<p style='color:#6b7280'>No OPA result files found.</p>"

    return f"""
<div class="section-header"><h2>OPA Policy Results</h2></div>
{''.join(parts)}
"""


def main():
    security   = load_json("security_report.json")
    dashboard  = load_json("compliance_dashboard_latest.json")

    drift_files = {
        "nsg_drift":     load_json("nsg_drift.json"),
        "storage_drift": load_json("storage_drift.json"),
        "scaling_drift": load_json("scaling_drift.json"),
        "iam_drift":     load_json("iam_drift.json"),
    }

    opa_files = {
        "opa_cis_result":  load_json("opa_cis_result.json"),
        "opa_vm_result":   load_json("opa_vm_result.json"),
        "opa_tags_result": load_json("opa_tags_result.json"),
    }

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CSPM Security Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #f8fafc; color: #1e293b; }}
  header {{ background: linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
            color:#fff; padding:24px 32px; display:flex; align-items:center;
            justify-content:space-between; }}
  header h1 {{ font-size:22px; font-weight:700; letter-spacing:.5px; }}
  header span {{ font-size:12px; color:#94a3b8; }}
  nav {{ background:#fff; border-bottom:1px solid #e2e8f0;
         display:flex; gap:0; overflow-x:auto; }}
  nav a {{ padding:14px 22px; text-decoration:none; color:#64748b; font-size:14px;
           font-weight:500; border-bottom:3px solid transparent; white-space:nowrap; }}
  nav a:hover, nav a.active {{ color:#3b82f6; border-bottom-color:#3b82f6; }}
  .search-bar {{ background:#fff; border-bottom:1px solid #e2e8f0; padding:10px 32px; }}
  .search-bar input {{ width:100%;max-width:400px; padding:8px 14px; border:1px solid #e2e8f0;
                       border-radius:8px; font-size:13px; outline:none; }}
  .search-bar input:focus {{ border-color:#3b82f6; }}
  main {{ padding:28px 32px; }}
  .tab-content {{ display:none; }}
  .tab-content.active {{ display:block; }}
  .section-header {{ margin-bottom:20px; }}
  .section-header h2 {{ font-size:20px; font-weight:700; color:#0f172a;
                        margin-bottom:4px; }}
  .card-row {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:28px; }}
  .card {{ background:#fff; border:1px solid #e5e7eb; border-radius:12px;
           padding:20px 28px; min-width:130px; flex:1;
           border-top:4px solid #e5e7eb; }}
  .card.pass  {{ border-top-color:#22c55e; }}
  .card.fail  {{ border-top-color:#ef4444; }}
  .card.skip  {{ border-top-color:#9ca3af; }}
  .card.error {{ border-top-color:#f97316; }}
  .card-num   {{ font-size:32px; font-weight:800; color:#0f172a; line-height:1; }}
  .card-label {{ font-size:12px; color:#6b7280; margin-top:6px; text-transform:uppercase;
                 letter-spacing:.5px; }}
  .chart-row  {{ display:flex; gap:20px; flex-wrap:wrap; margin-bottom:28px; }}
  .chart-box  {{ background:#fff; border:1px solid #e5e7eb; border-radius:12px;
                 padding:20px; flex:1; min-width:260px; max-width:480px; }}
  .chart-box h3 {{ font-size:14px; font-weight:600; color:#374151; margin-bottom:14px; }}
  .table-wrap {{ overflow-x:auto; border-radius:10px; border:1px solid #e5e7eb;
                 background:#fff; margin-bottom:24px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  thead tr {{ background:#f8fafc; }}
  th {{ padding:10px 14px; text-align:left; font-weight:600; color:#374151;
        font-size:12px; text-transform:uppercase; letter-spacing:.4px;
        border-bottom:1px solid #e5e7eb; white-space:nowrap; }}
  td {{ padding:10px 14px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
  tbody tr:last-child td {{ border-bottom:none; }}
  tbody tr:hover {{ background:#f8fafc; }}
  @media(max-width:768px){{
    main {{ padding:16px; }}
    .card-row, .chart-row {{ flex-direction:column; }}
  }}
</style>
</head>
<body>

<header>
  <h1>&#128737; CSPM Security Dashboard</h1>
  <span>Last updated: {now}</span>
</header>

<nav>
  <a href="#" class="active" onclick="showTab('tab-security',this)">Static Analysis</a>
  <a href="#" onclick="showTab('tab-compliance',this)">Compliance Dashboard</a>
  <a href="#" onclick="showTab('tab-drift',this)">Drift Detection</a>
  <a href="#" onclick="showTab('tab-opa',this)">OPA Policies</a>
</nav>

<div class="search-bar">
  <input id="globalSearch" type="search" placeholder="Filter table rows across all tabs...">
</div>

<main>
  <div id="tab-security" class="tab-content active">
    {build_security_section(security)}
  </div>
  <div id="tab-compliance" class="tab-content">
    {build_compliance_section(dashboard)}
  </div>
  <div id="tab-drift" class="tab-content">
    {build_drift_section(drift_files)}
  </div>
  <div id="tab-opa" class="tab-content">
    {build_opa_section(opa_files)}
  </div>
</main>

<script>
function showTab(id, el) {{
  document.querySelectorAll('.tab-content').forEach(function(t){{ t.classList.remove('active'); }});
  document.querySelectorAll('nav a').forEach(function(a){{ a.classList.remove('active'); }});
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
  return false;
}}

// Global search across visible rows
document.getElementById('globalSearch').addEventListener('input', function() {{
  var q = this.value.toLowerCase();
  document.querySelectorAll('.tab-content.active tbody tr').forEach(function(r) {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});
</script>
</body>
</html>
"""

    out = os.path.join(OUTPUTS, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Dashboard UI] Written to {out}")


if __name__ == "__main__":
    main()
