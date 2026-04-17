import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
FILE_PATH  = os.path.join(BASE_DIR, "nse500list.csv")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Timestamp (IST) ──────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(IST)
timestamp_str  = now_ist.strftime("%Y-%m-%d_%H-%M")   # for filename
display_time   = now_ist.strftime("%d-%b-%Y  %I:%M %p IST")

# ── Output file ──────────────────────────────────────────────────────────────
output_csv  = os.path.join(REPORTS_DIR, f"{timestamp_str}.csv")

# ── Main logic ───────────────────────────────────────────────────────────────
try:
    df_stocks = pd.read_csv(FILE_PATH)
    tickers   = [str(s).strip() + ".NS" for s in df_stocks["Symbol"]]

    results = []
    print(f"[{display_time}] Analysing {len(tickers)} stocks …")

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="15d")
            if hist.empty or len(hist) < 11:
                continue

            current_price  = hist["Close"].iloc[-1]
            previous_close = hist["Close"].iloc[-2]
            current_volume = hist["Volume"].iloc[-1]
            avg_10d_volume = hist["Volume"].iloc[-11:-1].mean()

            if current_price > previous_close and current_volume > 1.5 * avg_10d_volume:
                pct_gain    = ((current_price - previous_close) / previous_close) * 100
                vol_surge_x = round(current_volume / avg_10d_volume, 2)

                results.append({
                    "Ticker":            ticker.replace(".NS", ""),
                    "Current Price (₹)": round(current_price,  2),
                    "Prev Close (₹)":    round(previous_close, 2),
                    "Gain %":            round(pct_gain,        2),
                    "Volume":            int(current_volume),
                    "10D Avg Volume":    int(avg_10d_volume),
                    "Vol Surge (x)":     vol_surge_x,
                    "Scan Time (IST)":   display_time,
                })
        except Exception:
            continue

    final_df = pd.DataFrame(results)

    if not final_df.empty:
        final_df = final_df.sort_values("Gain %", ascending=False).reset_index(drop=True)
        print(f"  ✓ {len(final_df)} stocks found — saving to {output_csv}")
    else:
        # Save an empty CSV so the scan run is still recorded
        final_df = pd.DataFrame(columns=[
            "Ticker", "Current Price (₹)", "Prev Close (₹)", "Gain %",
            "Volume", "10D Avg Volume", "Vol Surge (x)", "Scan Time (IST)"
        ])
        print("  No stocks met the criteria — saving empty report.")

    final_df.to_csv(output_csv, index=False)
    print(f"  Report saved → {output_csv}")

except FileNotFoundError:
    print(f"ERROR: nse500list.csv not found at {FILE_PATH}")
    raise
except Exception as e:
    print(f"ERROR: {e}")
    raise
