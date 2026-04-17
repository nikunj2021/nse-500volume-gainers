import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz
import urllib.parse  # 👈 Added for standalone HTML downloads

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FILE_PATH   = os.path.join(BASE_DIR, "nse500list.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Timestamp (IST) ──────────────────────────────────────────────────────────
IST           = pytz.timezone("Asia/Kolkata")
now_ist       = datetime.now(IST)
timestamp_str = now_ist.strftime("%Y-%m-%d_%H-%M")
display_time  = now_ist.strftime("%d-%b-%Y  %I:%M %p IST")

# Output files
output_csv    = os.path.join(REPORTS_DIR, f"{timestamp_str}.csv")
output_html   = os.path.join(REPORTS_DIR, f"{timestamp_str}.html")

EMPTY_COLS = ["Ticker", "Current Price (₹)", "Prev Close (₹)", "Gain %",
              "Volume", "10D Avg Volume", "Vol Surge (x)", "Scan Time (IST)"]

# ── Load tickers ─────────────────────────────────────────────────────────────
try:
    df_stocks = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"❌ Error: Could not find '{FILE_PATH}'. Check your repository/folder!")
    exit(1)

tickers   = [str(s).strip() + ".NS" for s in df_stocks["Symbol"]]
print(f"[{display_time}] Batch-downloading {len(tickers)} tickers ...")

# ── Batch Download ───────────────────────────────────────────────────────────
raw = yf.download(
    tickers,
    period="15d",
    group_by="ticker",
    auto_adjust=True,
    threads=True, 
    progress=False,
)

print("  Download complete. Scanning ...")

results = []

for ticker in tickers:
    try:
        if len(tickers) == 1:
            hist = raw
        else:
            hist = raw[ticker]

        hist = hist.dropna(how="all")
        if hist.empty or len(hist) < 11:
            continue

        close  = hist["Close"]
        volume = hist["Volume"]

        current_price  = close.iloc[-1]
        previous_close = close.iloc[-2]
        current_volume = volume.iloc[-1]
        avg_10d_volume = volume.iloc[-11:-1].mean()

        if avg_10d_volume == 0:
            continue

        if current_price > previous_close and current_volume > 1.5 * avg_10d_volume:
            pct_gain    = ((current_price - previous_close) / previous_close) * 100
            vol_surge_x = round(current_volume / avg_10d_volume, 2)

            results.append({
                "Ticker":            ticker.replace(".NS", ""),
                "Current Price (₹)": round(float(current_price),  2),
                "Prev Close (₹)":    round(float(previous_close), 2),
                "Gain %":            round(float(pct_gain),        2),
                "Volume":            int(current_volume),
                "10D Avg Volume":    int(avg_10d_volume),
                "Vol Surge (x)":     vol_surge_x,
                "Scan Time (IST)":   display_time,
            })

    except Exception:
        continue

# ── Save & Generate HTML ─────────────────────────────────────────────────────
final_df = pd.DataFrame(results) if results else pd.DataFrame(columns=EMPTY_COLS)

if not final_df.empty:
    # Sort and save standard CSV to disk
    final_df = final_df.sort_values("Gain %", ascending=False).reset_index(drop=True)
    final_df.to_csv(output_csv, index=False)
    
    print(f"  ✓ {len(final_df)} stocks found")

    # Encode CSV data as data URI for optional inline download button
    csv_string = final_df.to_csv(index=False)
    encoded_csv = urllib.parse.quote(csv_string)
    data_uri = f"data:text/csv;charset=utf-8,{encoded_csv}"
    download_filename = f"Volume_Gainers_{timestamp_str}.csv"

    # ── Build HTML rows with colour-coded % Change ────────────────────────────
    def gain_bg(pct):
        """Return a green background shade based on gain magnitude."""
        if   pct >= 5:  return "#1a7a3c"   # dark green  – strong
        elif pct >= 3:  return "#27ae60"   # medium green
        elif pct >= 1:  return "#82c99f"   # light green
        else:           return "#c8ecd5"   # very light green

    rows_html = ""
    for i, row in enumerate(final_df.itertuples(index=False)):
        bg_row   = "#ffffff" if i % 2 == 0 else "#f7f9f8"
        gain_pct = row[3]   # index: Gain %
        gain_col = gain_bg(gain_pct)
        vol_m    = round(row[4] / 1_000_000, 2)      # Volume → millions
        sma_m    = round(row[5] / 1_000_000, 2)      # 10D Avg → millions
        rows_html += (
            f'<tr style="background:{bg_row}">'
            f'<td>{row[0]}</td>'                              # Symbol
            f'<td>₹ {row[1]:,.2f}</td>'                      # Current Price
            f'<td><span class="badge" style="background:{gain_col}">{gain_pct:+.2f}%</span></td>'
            f'<td>{vol_m:.2f}</td>'                           # Volume (M)
            f'<td>{sma_m:.2f}</td>'                           # 10D SMA (M)
            f'</tr>\n'
        )

    stock_count = len(final_df)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Volume Gainers – {display_time}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{
      height: 100%;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f0f2f1;
      color: #2c3e50;
      display: flex;
      flex-direction: column;
    }}

    /* ── Sticky top bar ──────────────────────────────────────────────────── */
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: #1b2a38;
      color: #ecf0f1;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.35);
      flex-shrink: 0;
    }}
    .topbar-left   {{ display: flex; align-items: center; gap: 14px; }}
    .topbar-title  {{ font-size: 1.1rem; font-weight: 700; letter-spacing: 0.3px; }}
    .topbar-meta   {{ font-size: 0.78rem; color: #95a5a6; }}
    .topbar-badge  {{
      background: #2ecc71; color: #fff;
      font-size: 0.72rem; font-weight: 600;
      padding: 3px 9px; border-radius: 20px;
    }}

    /* optional download – subtle text link */
    .btn-download {{
      font-size: 0.78rem; color: #7fb3d3;
      text-decoration: none; white-space: nowrap;
      padding: 4px 10px; border: 1px solid #3d5a72;
      border-radius: 4px; transition: all 0.2s;
    }}
    .btn-download:hover {{ color: #fff; border-color: #7fb3d3; background: #3d5a72; }}

    /* ── Scrollable table area ───────────────────────────────────────────── */
    .scroll-area {{
      flex: 1;
      overflow-y: auto;
      overflow-x: auto;
      padding: 20px 24px 32px;
    }}

    table {{
      width: 100%;
      max-width: 900px;
      margin: 0 auto;
      border-collapse: collapse;
      font-size: 0.9rem;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}

    thead {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: #1e3a50;
      color: #ecf0f1;
    }}
    thead th {{
      padding: 12px 16px;
      text-align: left;
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      white-space: nowrap;
      border-bottom: 2px solid #2980b9;
    }}

    tbody td {{
      padding: 10px 16px;
      border-bottom: 1px solid #eaecee;
      white-space: nowrap;
    }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr:hover td {{ background: #eaf4fb !important; }}

    /* Symbol — bold */
    tbody td:first-child {{ font-weight: 600; }}

    /* % Change badge */
    .badge {{
      display: inline-block;
      color: #fff;
      padding: 3px 9px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.82rem;
      min-width: 62px;
      text-align: center;
    }}
  </style>
</head>
<body>

  <div class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">📈 NSE 500 — Volume Gainers</span>
      <span class="topbar-badge">{stock_count} stocks</span>
      <span class="topbar-meta">Scan: {display_time}</span>
    </div>
    <a href="{data_uri}" download="{download_filename}" class="btn-download">⬇ CSV</a>
  </div>

  <div class="scroll-area">
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Current Price (₹)</th>
          <th>Change %</th>
          <th>Volume (M)</th>
          <th>10D SMA Vol (M)</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

</body>
</html>"""

    # Save HTML output
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"  Saved CSV  -> {output_csv}")
    print(f"  Saved HTML -> {output_html}")

else:
    print("  No stocks met the criteria — saving empty report.")
    final_df.to_csv(output_csv, index=False)
    print(f"  Saved -> {output_csv}")
