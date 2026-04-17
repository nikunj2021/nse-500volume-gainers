import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "nse500list.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Ensure the output directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)
output_csv = os.path.join(REPORTS_DIR, "Volume_Gainers_Latest.csv")

# ── Timestamp (IST) ──────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(IST)
display_time = now_ist.strftime("%d-%b-%Y  %I:%M %p IST")

# ── Load tickers ─────────────────────────────────────────────────────────────
try:
    df_stocks = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"❌ Error: Could not find '{FILE_PATH}'. Check your file path.")
    exit(1)

tickers = [str(s).strip() + ".NS" for s in df_stocks["Symbol"]]
print(f"[{display_time}] Scanning {len(tickers)} tickers for volume breakouts...")

# ── Batch Download ───────────────────────────────────────────────────────────
raw = yf.download(
    tickers,
    period="15d",
    group_by="ticker",
    auto_adjust=True,
    threads=True, 
    progress=False,
)

results = []

# ── Data Processing ──────────────────────────────────────────────────────────
for ticker in tickers:
    try:
        hist = raw if len(tickers) == 1 else raw[ticker]
        hist = hist.dropna(how="all")
        
        if hist.empty or len(hist) < 11:
            continue

        close = hist["Close"]
        volume = hist["Volume"]

        current_price = close.iloc[-1]
        previous_close = close.iloc[-2]
        current_volume = volume.iloc[-1]
        avg_10d_volume = volume.iloc[-11:-1].mean()

        if avg_10d_volume == 0:
            continue

        if current_price > previous_close and current_volume > 1.5 * avg_10d_volume:
            pct_gain = ((current_price - previous_close) / previous_close) * 100

            results.append({
                "Ticker Name": ticker.replace(".NS", ""),
                "Current Price": round(float(current_price), 2),
                "Gain %": round(float(pct_gain), 2),
                "Volume": int(current_volume),
                "10 Days Avg Volume": int(avg_10d_volume)
            })

    except Exception:
        continue

# ── Save CSV ─────────────────────────────────────────────────────────────────
if results:
    final_df = pd.DataFrame(results)
    final_df = final_df.sort_values("Gain %", ascending=False).reset_index(drop=True)
    final_df.to_csv(output_csv, index=False)
    print(f"  ✓ {len(final_df)} stocks found. Saved to {output_csv}")
else:
    print("  No stocks met the criteria. Saving empty state.")
    # Saves a message so the frontend knows there's no data, rather than throwing a formatting error
    pd.DataFrame([{"Message": "No stocks met criteria at this time"}]).to_csv(output_csv, index=False)
