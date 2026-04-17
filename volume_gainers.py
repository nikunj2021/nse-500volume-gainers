import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FILE_PATH   = os.path.join(BASE_DIR, "nse500list.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Timestamp (IST) ──────────────────────────────────────────────────────────
IST          = pytz.timezone("Asia/Kolkata")
now_ist      = datetime.now(IST)
timestamp_str = now_ist.strftime("%Y-%m-%d_%H-%M")
display_time  = now_ist.strftime("%d-%b-%Y  %I:%M %p IST")
output_csv    = os.path.join(REPORTS_DIR, f"{timestamp_str}.csv")

EMPTY_COLS = ["Ticker", "Current Price (₹)", "Prev Close (₹)", "Gain %",
              "Volume", "10D Avg Volume", "Vol Surge (x)", "Scan Time (IST)"]

# ── Load tickers ─────────────────────────────────────────────────────────────
df_stocks = pd.read_csv(FILE_PATH)
tickers   = [str(s).strip() + ".NS" for s in df_stocks["Symbol"]]
print(f"[{display_time}]  Batch-downloading {len(tickers)} tickers ...")

# ── Single batch download (parallel under the hood) ──────────────────────────
raw = yf.download(
    tickers,
    period="15d",
    group_by="ticker",
    auto_adjust=True,
    threads=True,        # parallel fetch — key speed-up
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

# ── Save ─────────────────────────────────────────────────────────────────────
final_df = pd.DataFrame(results) if results else pd.DataFrame(columns=EMPTY_COLS)

if not final_df.empty:
    final_df = final_df.sort_values("Gain %", ascending=False).reset_index(drop=True)
    print(f"  ✓ {len(final_df)} stocks found")
else:
    print("  No stocks met the criteria — saving empty report.")

final_df.to_csv(output_csv, index=False)
print(f"  Saved -> {output_csv}")
