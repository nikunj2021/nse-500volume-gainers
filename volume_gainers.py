import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz
import requests

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

# ── Save CSV & Send Telegram Alert ───────────────────────────────────────────
if results:
    final_df = pd.DataFrame(results)
    final_df = final_df.sort_values("Gain %", ascending=False).reset_index(drop=True)
    final_df.to_csv(output_csv, index=False)
    print(f"  ✓ {len(final_df)} stocks found. Saved to {output_csv}")

    # --- TELEGRAM HTML ALERT ---
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    if BOT_TOKEN and CHAT_ID:
        messages = []
        current_msg = f"<b>📈 NSE Volume Gainers</b>\n<i>{display_time}</i>\n\n"
        
        # Iterate through ALL rows, no limits
        for idx, row in final_df.iterrows():
            vol_str = f"{row['Volume']/1000000:.1f}M" if row['Volume'] > 1000000 else f"{row['Volume']/1000:.1f}K"
            avg_str = f"{row['10 Days Avg Volume']/1000000:.1f}M" if row['10 Days Avg Volume'] > 1000000 else f"{row['10 Days Avg Volume']/1000:.1f}K"
            
            row_text = f"🟢 <b>{row['Ticker Name']}</b> : ₹{row['Current Price']} (<b>+{row['Gain %']}%</b>)\n      └ Vol: {vol_str} <i>(Avg: {avg_str})</i>\n\n"
            
            # Telegram's character limit is 4096. We split at ~4000 to be safe.
            if len(current_msg) + len(row_text) > 4000:
                messages.append(current_msg)
                current_msg = row_text # Start a new message chunk
            else:
                current_msg += row_text
                
        # Append the final chunk if it contains data
        if current_msg:
            messages.append(current_msg)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # Send each message chunk sequentially
        for i, m in enumerate(messages):
            payload = {
                "chat_id": CHAT_ID,
                "text": m,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            try:
                resp = requests.post(url, json=payload)
                resp.raise_for_status()
                print(f"  ✓ Telegram alert part {i+1}/{len(messages)} sent successfully.")
            except Exception as e:
                print(f"  ❌ Failed to send Telegram alert part {i+1}: {e}")
    else:
        print("  ⚠️ Telegram credentials missing. Skipping alert.")
else:
    print("  No stocks met the criteria. Saving empty state.")
    pd.DataFrame([{"Message": "No stocks met criteria at this time"}]).to_csv(output_csv, index=False)