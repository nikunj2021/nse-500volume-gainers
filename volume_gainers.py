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

    # 🟢 NEW: Encode CSV data directly for the HTML button
    csv_string = final_df.to_csv(index=False)
    encoded_csv = urllib.parse.quote(csv_string)
    data_uri = f"data:text/csv;charset=utf-8,{encoded_csv}"
    download_filename = f"Volume_Gainers_{timestamp_str}.csv"

    # Format Data specifically for HTML requirements
    html_df = pd.DataFrame()
    html_df["Symbol"] = final_df["Ticker"]
    html_df["Current Price"] = final_df["Current Price (₹)"]
    html_df["Percentage Change (%)"] = final_df["Gain %"]
    html_df["Volume (in million)"] = (final_df["Volume"] / 1_000_000).round(2)
    html_df["10 days SMA volume (in million)"] = (final_df["10D Avg Volume"] / 1_000_000).round(2)

    # Render HTML template with CSS
    table_html = html_df.to_html(index=False, border=0, classes="styled-table")

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Volume Gainers - {display_time}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }}
            .container {{ max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ececec; padding-bottom: 15px; margin-bottom: 20px; }}
            h2 {{ margin: 0; color: #2c3e50; }}
            .btn-download {{ background-color: #27ae60; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; transition: background 0.3s; display: inline-block; cursor: pointer; }}
            .btn-download:hover {{ background-color: #219150; }}
            .table-wrapper {{ overflow-x: auto; max-height: 600px; overflow-y: auto; border: 1px solid #ddd; border-radius: 5px; }}
            .styled-table {{ width: 100%; border-collapse: collapse; font-size: 0.95em; text-align: left; }}
            .styled-table thead {{ position: sticky; top: 0; background-color: #2980b9; color: #ffffff; z-index: 1; }}
            .styled-table th, .styled-table td {{ padding: 12px 15px; border-bottom: 1px solid #dddddd; }}
            .styled-table tbody tr:nth-of-type(even) {{ background-color: #f9f9f9; }}
            .styled-table tbody tr:hover {{ background-color: #f1f1f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📈 NSE 500 Volume Gainers</h2>
                <a href="{data_uri}" download="{download_filename}" class="btn-download">📥 Download CSV</a>
            </div>
            <p><strong>Scan Time:</strong> {display_time}</p>
            
            <div class="table-wrapper">
                {table_html}
            </div>
            
        </div>
    </body>
    </html>
    """

    # Save HTML output
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"  Saved CSV  -> {output_csv}")
    print(f"  Saved HTML -> {output_html}")

else:
    print("  No stocks met the criteria — saving empty report.")
    final_df.to_csv(output_csv, index=False)
    print(f"  Saved -> {output_csv}")
