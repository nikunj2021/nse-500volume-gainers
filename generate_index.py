"""
Reads every CSV in ./reports/ and rebuilds index.html.
Run this after volume_gainers.py in the GitHub Actions workflow.
"""

import os, csv
from datetime import datetime
import pytz

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
INDEX_FILE  = os.path.join(BASE_DIR, "index.html")

IST          = pytz.timezone("Asia/Kolkata")
generated_at = datetime.now(IST).strftime("%d-%b-%Y  %I:%M %p IST")

# ── Collect all CSVs ─────────────────────────────────────────────────────────
reports = []
if os.path.isdir(REPORTS_DIR):
    for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
        if fname.endswith(".csv"):
            fpath    = os.path.join(REPORTS_DIR, fname)
            filesize = os.path.getsize(fpath)

            # Count data rows (exclude header)
            row_count = 0
            try:
                with open(fpath, newline="") as f:
                    reader = csv.reader(f)
                    rows   = list(reader)
                    row_count = max(0, len(rows) - 1)
            except Exception:
                pass

            # Parse timestamp from filename  2025-06-10_09-30
            name_no_ext = fname[:-4]
            try:
                dt = datetime.strptime(name_no_ext, "%Y-%m-%d_%H-%M")
                label = dt.strftime("%d %b %Y — %I:%M %p")
            except ValueError:
                label = name_no_ext

            reports.append({
                "fname":     fname,
                "label":     label,
                "rows":      row_count,
                "size_kb":   round(filesize / 1024, 1),
            })

# ── Group by date ────────────────────────────────────────────────────────────
from collections import defaultdict
by_date = defaultdict(list)
for r in reports:
    date_key = r["fname"][:10]   # YYYY-MM-DD
    by_date[date_key].append(r)

# ── Build HTML ───────────────────────────────────────────────────────────────
rows_html = ""
for date_key in sorted(by_date.keys(), reverse=True):
    try:
        date_label = datetime.strptime(date_key, "%Y-%m-%d").strftime("%A, %d %b %Y")
    except Exception:
        date_label = date_key

    rows_html += f"""
      <tr class="date-header">
        <td colspan="4">📅 {date_label}</td>
      </tr>"""

    for r in by_date[date_key]:
        badge_class = "badge-empty" if r["rows"] == 0 else "badge-found"
        badge_text  = "No Results" if r["rows"] == 0 else f"{r['rows']} stocks"
        rows_html += f"""
      <tr>
        <td><a href="reports/{r['fname']}" download>⬇ {r['label']}</a></td>
        <td><span class="badge {badge_class}">{badge_text}</span></td>
        <td>{r['size_kb']} KB</td>
        <td><a href="reports/{r['fname']}" target="_blank">View</a></td>
      </tr>"""

if not rows_html:
    rows_html = '<tr><td colspan="4" style="text-align:center;color:#888;">No reports generated yet. First run pending.</td></tr>'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NSE Volume Gainers — Reports</title>
  <style>
    :root {{
      --bg:      #0d1117;
      --card:    #161b22;
      --border:  #30363d;
      --accent:  #58a6ff;
      --green:   #3fb950;
      --red:     #f85149;
      --muted:   #8b949e;
      --text:    #e6edf3;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: var(--card);
      border-bottom: 1px solid var(--border);
      padding: 24px 32px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .logo {{ font-size: 2rem; }}
    header h1 {{ font-size: 1.4rem; font-weight: 700; }}
    header p  {{ color: var(--muted); font-size: 0.85rem; margin-top: 2px; }}

    /* ── Stats bar ── */
    .stats {{
      display: flex;
      gap: 24px;
      padding: 16px 32px;
      background: var(--card);
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .num  {{ font-size: 1.5rem; font-weight: 700; color: var(--accent); }}
    .stat .lbl  {{ font-size: 0.75rem; color: var(--muted); margin-top: 2px; }}

    /* ── Main ── */
    main {{ padding: 32px; max-width: 900px; margin: 0 auto; }}
    h2   {{ font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: var(--muted); letter-spacing: .05em; text-transform: uppercase; }}

    /* ── Table ── */
    table    {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }}
    th       {{ background: #1c2128; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: .06em; padding: 10px 16px; text-align: left; }}
    td       {{ padding: 11px 16px; font-size: 0.88rem; border-top: 1px solid var(--border); }}
    tr:hover td {{ background: #1c2128; }}
    a        {{ color: var(--accent); text-decoration: none; }}
    a:hover  {{ text-decoration: underline; }}

    /* Date group header */
    tr.date-header td {{
      background: #0d1117;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: .04em;
      padding: 8px 16px;
      border-top: 2px solid var(--border);
    }}

    /* ── Badges ── */
    .badge        {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
    .badge-found  {{ background: rgba(63,185,80,.15); color: var(--green); border: 1px solid rgba(63,185,80,.3); }}
    .badge-empty  {{ background: rgba(139,148,158,.1); color: var(--muted);  border: 1px solid var(--border); }}

    /* ── Footer ── */
    footer {{ text-align: center; padding: 24px; color: var(--muted); font-size: 0.78rem; }}

    /* ── Info box ── */
    .info-box {{
      background: rgba(88,166,255,.07);
      border: 1px solid rgba(88,166,255,.25);
      border-radius: 8px;
      padding: 14px 18px;
      font-size: 0.84rem;
      color: var(--muted);
      margin-bottom: 24px;
      line-height: 1.6;
    }}
    .info-box strong {{ color: var(--accent); }}
  </style>
</head>
<body>

<header>
  <div class="logo">📊</div>
  <div>
    <h1>NSE Volume Gainers — Report Hub</h1>
    <p>Auto-generated every 15 minutes · Mon–Fri · 9:30 AM – 3:15 PM IST</p>
  </div>
</header>

<div class="stats">
  <div class="stat"><div class="num">{len(reports)}</div><div class="lbl">Total Scans</div></div>
  <div class="stat"><div class="num">{len(by_date)}</div><div class="lbl">Trading Days</div></div>
  <div class="stat"><div class="num">{sum(r['rows'] for r in reports)}</div><div class="lbl">Total Hits</div></div>
  <div class="stat"><div class="num" style="font-size:1rem">{generated_at}</div><div class="lbl">Last Updated</div></div>
</div>

<main>
  <div class="info-box">
    <strong>Criteria:</strong> Price &gt; Prev Close &amp;&amp; Current Volume &gt; <strong>1.5×</strong> 10-day Average Volume.
    Stocks sourced from <strong>NSE 500</strong> universe. Click ⬇ to download any CSV report.
  </div>

  <h2>📁 All Reports</h2>
  <table>
    <thead>
      <tr>
        <th>Scan Time</th>
        <th>Stocks Found</th>
        <th>File Size</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</main>

<footer>
  Auto-refreshed by GitHub Actions · NSE market hours only ·
  <a href="https://github.com" target="_blank">View Workflow Runs</a>
</footer>

</body>
</html>
"""

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"index.html regenerated — {len(reports)} reports listed.")
