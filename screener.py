#!/usr/bin/env python3
"""
NSE 500 Volume Gainer Screener
Author  : Nikunj | github.com/nikunj2021
Repo    : nse-500volume-gainers
Schedule: Every 15 min during NSE market hours via crontab
"""

import yfinance as yf
import pandas as pd
import requests
import pytz
import json
import os
import subprocess
import gc
import logging
import time
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = "8985262215:AAEHd-HzD6qMeIMfmCi46_QZVAEOCUOxvys"
TELEGRAM_CHATID = "653352464"
TELEGRAM_CHATID = "-1003864987520"
GITHUB_USER     = "nikunj2021"
GITHUB_REPO     = "nse-500volume-gainers"

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PREV_FILE       = os.path.join(BASE_DIR, "prev_results.json")
HTML_FILE       = os.path.join(BASE_DIR, "index.html")

# Screening filters
MIN_VOLUME      = 100_000          # minimum current volume
VOL_RATIO_MIN   = 1.5              # current vol must be >= 1.5x 10D avg
MIN_MKTCAP_CR   = 5_000            # minimum market cap in Crore
MIN_MKTCAP_INR  = MIN_MKTCAP_CR * 1_00_00_000   # 5000 Cr in INR = 5e10

IST             = pytz.timezone("Asia/Kolkata")
BATCH           = 25               # stocks per batch — keeps RAM within 1 GB

# ─────────────────────────────────────────────────────────────────────────────
# NIFTY 500 UNIVERSE  (~480 symbols)
# ─────────────────────────────────────────────────────────────────────────────
_RAW = [
    # ── Nifty 50 ─────────────────────────────────────────────────────────────
    "RELIANCE","TCS","HDFCBANK","BHARTIARTL","ICICIBANK","INFOSYS","SBIN",
    "HINDUNILVR","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI",
    "HCLTECH","SUNPHARMA","ADANIENT","TATAMOTORS","WIPRO","ONGC","NTPC",
    "POWERGRID","ULTRACEMCO","TITAN","BAJAJFINSV","M&M","NESTLEIND","TECHM",
    "JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BPCL","GRASIM","DIVISLAB",
    "DRREDDY","CIPLA","EICHERMOT","APOLLOHOSP","BAJAJ-AUTO","BRITANNIA",
    "SHRIRAMFIN","TATACONSUM","ADANIPORTS","HEROMOTOCO","ASIANPAINT",
    "INDUSINDBK","LTIM","HDFCLIFE","SBILIFE",

    # ── Nifty Next 50 ────────────────────────────────────────────────────────
    "ADANIGREEN","ADANIPOWER","AMBUJACEM","ATGL","BANKBARODA","BERGEPAINT",
    "BEL","BOSCHLTD","CANBK","CHOLAFIN","COLPAL","DLF","DMART","GAIL",
    "GODREJCP","GODREJPROP","HAL","HAVELLS","HDFCAMC","ICICIPRULI","ICICIGI",
    "INDHOTEL","IOC","IRFC","JINDALSTEL","JSWENERGY","LICI","LUPIN",
    "MCDOWELL-N","MFSL","MOTHERSON","MUTHOOTFIN","NAUKRI","OBEROIRLTY",
    "OFSS","PAGEIND","PFC","PIDILITIND","PIIND","PNB","POLYCAB","RECLTD",
    "SAIL","SIEMENS","SRF","TORNTPHARM","TRENT","TVSMOTOR","UPL","VEDL",

    # ── Nifty Midcap 150 ─────────────────────────────────────────────────────
    "ABCAPITAL","ABFRL","AIAENG","AJANTPHARM","ALKEM","APLLTD","ASTRAL",
    "AUROPHARMA","BALKRISIND","BANDHANBNK","BATAINDIA","BHARATFORG","BHEL",
    "BIOCON","BLUEDART","BSOFT","CANFINHOME","CASTROLIND","CEATLTD",
    "CENTRALBK","COFORGE","CONCOR","CROMPTON","CUMMINSIND","CYIENT",
    "DALBHARAT","DEEPAKNTR","ECLERX","EMAMILTD","ENDURANCE","ENGINERSIN",
    "ESCORTS","EXIDEIND","FEDERALBNK","FLUOROCHEM","GLENMARK","GMRINFRA",
    "GRANULES","GSPL","HAPPSTMNDS","HFCL","HINDCOPPER","HINDPETRO",
    "IDFCFIRSTB","IEX","INDIAMART","INDIGO","IPCALAB","IRB","JKCEMENT",
    "JKTYRE","JUBLFOOD","KAJARIACER","KANSAINER","KEI","LAURUSLABS",
    "LICHSGFIN","LALPATHLAB","LTTS","LUXIND","MARICO","MAXHEALTH",
    "METROPOLIS","MPHASIS","MRF","NATCOPHARM","NBCC","NCC","NMDC",
    "NYKAA","PERSISTENT","PETRONET","PFIZER","PHOENIXLTD","PNBHOUSING",
    "PRESTIGE","PVRINOX","RADICO","RAILTEL","RITES","SAFARI","SCHAEFFLER",
    "SJVN","SKFINDIA","SOBHA","SOLARINDS","SONACOMS","SUNTV","SUPREMEIND",
    "SUNDARMFIN","SUNDRMFAST","TATACHEM","TATACOMM","TATAELXSI","TATAPOWER",
    "THERMAX","TIMKEN","TORNTPOWER","UBL","UJJIVANSFB","UNIONBANK","UTIAMC",
    "VBL","VOLTAS","WELCORP","WELSPUNLIV","YESBANK","ZEEL","ZYDUSLIFE",

    # ── Nifty Smallcap & additional NSE 500 ──────────────────────────────────
    "AAVAS","ABBOTINDIA","AFFLE","ANGELONE","ANURAS","APOLLOTYRE","ARVIND",
    "ASHOKLEY","ATUL","AUBANK","AVANTIFEED","BAJAJHLDNG","BALRAMCHIN",
    "BAYERCROP","BRIGADE","BSE","CAMPUS","CARTRADE","CDSL","CESC","CGPOWER",
    "CHAMBLFERT","CLEAN","CREDITACC","CRISIL","DATAPATTNS","DCMSHRIRAM",
    "DELHIVERY","DEVYANI","DHANUKA","DIXON","EASEMYTRIP","EIDPARRY",
    "ELECON","ELGIEQUIP","EMCURE","EPL","EQUITAS","ERIS","ETHOSLTD",
    "FINEORG","FORTIS","FUSION","GALAXYSURF","GHCL","GICRE","GLAND",
    "GODREJIND","GPPL","GREENPANEL","GRINDWELL","GSFC","GUJGASLTD",
    "HAPPYFORGE","HBLPOWER","HEIDELBERG","HIKAL","HOMEFIRST","HONASA",
    "IBREALEST","ICRA","IDBI","IDFC","IFBIND","INDIACEM","INDNIPPON",
    "INOXGREEN","INOXINDIA","INOXWIND","INTELLECT","IOB","ITDCEM",
    "J&KBANK","JBCHEPHARM","JKPAPER","JMFINANCIL","JPPOWER","JSWINFRA",
    "KFINTECH","KIRLOSENG","KNRCON","KOLTEPATIL","KRBL","KRCL","LATENTVIEW",
    "LEMONTREE","LTFH","MAHLIFE","MANAPPURAM","MANKIND","MAPMYINDIA",
    "MARKSANS","MASTEK","MAYURUNIQ","MEDANTA","MEDPLUS","MIDHANI",
    "MINDACORP","MOLDTKPAC","MOTILALOFS","MSTCLTD","MTARTECH","NAM-INDIA",
    "NAVINFLUOR","NAZARA","NESCO","NETWORK18","NEWGEN","NIITLTD","NILKAMAL",
    "NLCINDIA","NOCIL","NUVOCO","OLECTRA","ORIENTELEC","PAYTM","PEL",
    "PENIND","PGHH","PRAJIND","PRICOLLTD","PRINCEPIPE","PRSMJOHNSN",
    "PSPPROJECT","PURVA","QUESS","RATNAMANI","RAYMOND","REDINGTON","RELAXO",
    "ROLEXRINGS","ROSSARI","SAREGAMA","SBICARD","SHAKTIPUMP","SHOPERSTOP",
    "SHREECEM","SHTF","SKIPPER","SPANDANA","SPARC","SPICEJET","STLTECH",
    "SUDARSCHEM","SUMICHEM","SYMPHONY","TANLA","TATAINVEST","TATAMETALI",
    "TDPOWERSYS","TEJASNET","THYROCARE","TIINDIA","TINPLATE","TRIDENT",
    "TRIVENI","TVTODAY","UGROCAP","UNICHEMLAB","UNITDSPR","UNOMINDA",
    "USHAMART","VAIBHAVGBL","VARROC","VGUARD","VINATIORGA","VMART",
    "VOLTAMP","VSTIND","WABAG","WEBELSOLAR","WELSPUNIND","WESTLIFE",
    "WONDERLA","ZAGGLE","ZENSARTECH","ZYDUSWELL","DEEPAKFERT","SAPPHIRE",
    "EQUITASBNK","MANYAVAR","DOMS","NIACL","MMFL","CGCL","AKUMS",
    "JSWHL","SENCO","POLICYBZR","NUVAMA","SAMHI","SIGNATURE","INDIGOPNTS",
    "KAYNES","SBCL","APARINDS","ROUTE","GPPL","SWSOLAR","BIKAJI",
    "CAMPUS","DREAMFOLKS","MANKIND","GLOBAL","MEDPLUS","YATHARTH",
]

# Deduplicate and append .NS
SYMBOLS = list(dict.fromkeys(_RAW))
NS_SYMBOLS = [s + ".NS" for s in SYMBOLS]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    open_t  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


def send_telegram(text: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            json={"chat_id": TELEGRAM_CHATID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        log.error(f"Telegram error: {e}")


def load_prev() -> set:
    try:
        with open(PREV_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_prev(symbols: set):
    with open(PREV_FILE, "w") as f:
        json.dump(sorted(symbols), f)


# ─────────────────────────────────────────────────────────────────────────────
# STOCK FETCHER  (single stock, all exceptions caught)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_stock(symbol: str) -> dict | None:
    try:
        ticker  = yf.Ticker(symbol)
        fi      = ticker.fast_info

        cur_vol  = fi.last_volume   or 0
        mktcap   = fi.market_cap    or 0
        price    = fi.last_price    or 0
        prev_cls = fi.previous_close or price

        # Quick pre-checks before heavier history call
        if cur_vol  < MIN_VOLUME:    return None
        if mktcap   < MIN_MKTCAP_INR: return None
        if price    <= 0:            return None

        # Historical daily data — last 15 trading days
        hist = ticker.history(period="15d", auto_adjust=True)
        if len(hist) < 11:
            return None

        avg_10d = hist["Volume"].iloc[-11:-1].mean()  # Previous 10 complete days
        if avg_10d <= 0:
            return None

        ratio = cur_vol / avg_10d
        if ratio < VOL_RATIO_MIN:
            return None

        pct        = ((price - prev_cls) / prev_cls * 100) if prev_cls else 0
        mktcap_cr  = mktcap / 1_00_00_000   # Convert INR → Crore

        return {
            "symbol"    : symbol.replace(".NS", ""),
            "price"     : round(price, 2),
            "pct"       : round(pct,   2),
            "cur_vol"   : int(cur_vol),
            "avg_vol"   : int(avg_10d),
            "ratio"     : round(ratio, 2),
            "mktcap_cr" : int(mktcap_cr),
        }

    except Exception as e:
        log.debug(f"Skip {symbol}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SCREENER  — batched for low memory
# ─────────────────────────────────────────────────────────────────────────────
def screen_stocks() -> list:
    results = []
    total   = len(NS_SYMBOLS)
    batches = (total + BATCH - 1) // BATCH

    log.info(f"Screening {total} stocks in {batches} batches of {BATCH}…")

    for i in range(0, total, BATCH):
        batch = NS_SYMBOLS[i : i + BATCH]
        b_num = i // BATCH + 1
        log.info(f"Batch {b_num}/{batches}  [{batch[0]} … {batch[-1]}]")

        for sym in batch:
            r = fetch_stock(sym)
            if r:
                results.append(r)
                log.info(
                    f"  ✅ {r['symbol']:20s} | "
                    f"Ratio: {r['ratio']:.2f}x | "
                    f"Vol: {r['cur_vol']:>12,} | "
                    f"MCap: ₹{r['mktcap_cr']:,} Cr"
                )

        gc.collect()
        time.sleep(0.3)   # polite delay between batches

    results.sort(key=lambda x: x["ratio"], reverse=True)
    log.info(f"Screening complete — {len(results)}/{total} passed filters")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# HTML GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_html(results: list, scan_time: datetime, total_screened: int) -> str:
    ist_str = scan_time.strftime("%d %b %Y  %I:%M:%S %p IST")
    mkt_open = is_market_open()
    mkt_badge_cls  = "badge-open"  if mkt_open else "badge-closed"
    mkt_badge_text = "🟢 MARKET OPEN" if mkt_open else "🔴 MARKET CLOSED"

    # Build table rows
    rows_html = ""
    for r in results:
        pct_color  = "#3fb950" if r["pct"] >= 0 else "#ff7b72"
        pct_sign   = "+" if r["pct"] >= 0 else ""

        if   r["ratio"] >= 4.0: ratio_color = "#ff6d00"
        elif r["ratio"] >= 3.0: ratio_color = "#f0a500"
        elif r["ratio"] >= 2.0: ratio_color = "#3fb950"
        else:                   ratio_color = "#79c0ff"

        tv = f"https://www.tradingview.com/chart/?symbol=NSE:{r['symbol']}"

        rows_html += f"""
        <tr>
          <td><a href="{tv}" target="_blank" class="sym">{r['symbol']}</a></td>
          <td class="num">₹{r['price']:,.2f}</td>
          <td class="num" style="color:{pct_color};font-weight:700">{pct_sign}{r['pct']}%</td>
          <td class="num">{r['cur_vol']:,}</td>
          <td class="num">{r['avg_vol']:,}</td>
          <td class="num" style="color:{ratio_color};font-weight:800">{r['ratio']}x</td>
          <td class="num">₹{r['mktcap_cr']:,} Cr</td>
        </tr>"""

    if not rows_html:
        rows_html = '<tr><td colspan="7" class="empty">No stocks passed the filter this scan</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="900">
<title>NSE Volume Gainer Screener</title>
<style>
:root{{
  --bg:#0d1117; --surface:#161b22; --border:#30363d;
  --text:#e6edf3; --muted:#8b949e;
  --blue:#58a6ff; --green:#3fb950; --red:#ff7b72; --orange:#f0a500;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}}

/* ── header ── */
.header{{
  background:linear-gradient(135deg,#161b22,#1c2128);
  padding:18px 28px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px
}}
.header h1{{font-size:1.45rem;font-weight:700;color:var(--blue)}}
.header h1 span{{color:var(--green)}}
.badges{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.badge{{padding:4px 13px;border-radius:20px;font-size:.78rem;font-weight:600}}
.badge-open{{background:#1a4731;color:var(--green);border:1px solid var(--green)}}
.badge-closed{{background:#3d1a1a;color:var(--red);border:1px solid var(--red)}}
.badge-info{{background:#1f3a5f;color:var(--blue);border:1px solid #388bfd}}

/* ── stat cards ── */
.stats{{display:flex;gap:14px;padding:18px 28px;flex-wrap:wrap}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;
       padding:14px 22px;flex:1;min-width:140px;text-align:center}}
.card .v{{font-size:1.7rem;font-weight:700;color:var(--blue)}}
.card .l{{font-size:.72rem;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}}

/* ── controls ── */
.controls{{display:flex;gap:10px;padding:14px 28px;align-items:center;flex-wrap:wrap}}
.search{{flex:1;min-width:200px;max-width:320px;padding:8px 13px;
         background:#21262d;border:1px solid var(--border);border-radius:6px;
         color:var(--text);font-size:.88rem;outline:none}}
.search:focus{{border-color:#388bfd}}
.btn{{padding:8px 20px;border:none;border-radius:6px;cursor:pointer;font-weight:600;
      font-size:.88rem;transition:opacity .2s}}
.btn-refresh{{background:#238636;color:#fff}}
.btn-refresh:hover{{opacity:.85}}
.time{{color:var(--muted);font-size:.78rem}}

/* ── table ── */
.wrap{{padding:0 28px 30px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:.88rem}}
thead th{{background:var(--surface);color:var(--muted);padding:9px 13px;
          text-align:left;border-bottom:2px solid var(--border);
          cursor:pointer;user-select:none;white-space:nowrap;
          font-weight:600;font-size:.73rem;text-transform:uppercase;letter-spacing:.5px}}
thead th:hover{{color:var(--blue)}}
tbody tr{{border-bottom:1px solid #21262d;transition:background .12s}}
tbody tr:hover{{background:var(--surface)}}
td{{padding:9px 13px;white-space:nowrap}}
.sym{{color:var(--blue);text-decoration:none;font-weight:700;font-size:.93rem}}
.sym:hover{{color:#79c0ff;text-decoration:underline}}
.num{{font-variant-numeric:tabular-nums}}
.empty{{text-align:center;color:var(--muted);padding:40px;font-size:.95rem}}

/* ── footer ── */
footer{{text-align:center;padding:18px;color:var(--muted);font-size:.73rem;
        border-top:1px solid #21262d}}

@media(max-width:600px){{
  .header,.stats,.controls,.wrap{{padding-left:14px;padding-right:14px}}
  .card .v{{font-size:1.3rem}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>📊 NSE <span>Volume Gainer</span> Screener</h1>
  <div class="badges">
    <span class="badge {mkt_badge_cls}">{mkt_badge_text}</span>
    <span class="badge badge-info">🔍 {total_screened} Screened</span>
  </div>
</div>

<div class="stats">
  <div class="card"><div class="v">{len(results)}</div><div class="l">Stocks Passing</div></div>
  <div class="card"><div class="v">{total_screened}</div><div class="l">Total Screened</div></div>
  <div class="card"><div class="v">1.5x</div><div class="l">Min Vol Ratio</div></div>
  <div class="card"><div class="v">5K Cr</div><div class="l">Min Mkt Cap</div></div>
</div>

<div class="controls">
  <input class="search" id="srch" placeholder="🔍  Search symbol…" oninput="filter()">
  <button class="btn btn-refresh" onclick="location.reload()">🔄 Refresh</button>
  <span class="time">Last scan: {ist_str} &nbsp;|&nbsp; Auto-refresh: 15 min</span>
</div>

<div class="wrap">
<table id="tbl">
  <thead>
    <tr>
      <th onclick="sort(0)">Symbol ↕</th>
      <th onclick="sort(1)">Price ↕</th>
      <th onclick="sort(2)">% Chg ↕</th>
      <th onclick="sort(3)">Cur Volume ↕</th>
      <th onclick="sort(4)">10D Avg Vol ↕</th>
      <th onclick="sort(5)">Vol Ratio ↕</th>
      <th onclick="sort(6)">Mkt Cap ↕</th>
    </tr>
  </thead>
  <tbody id="tb">{rows_html}</tbody>
</table>
</div>

<footer>
  Filters: Volume ≥ 1,00,000 &nbsp;|&nbsp; Vol Ratio ≥ 1.5x &nbsp;|&nbsp;
  Mkt Cap &gt; ₹5,000 Cr &nbsp;|&nbsp; Data: Yahoo Finance &nbsp;|&nbsp;
  github.com/{GITHUB_USER}/{GITHUB_REPO}
</footer>

<script>
const dir = {{}};
function sort(c){{
  const tb=document.getElementById('tb');
  const rows=[...tb.querySelectorAll('tr')];
  dir[c]=!dir[c];
  rows.sort((a,b)=>{{
    const av=a.cells[c]?.innerText||'', bv=b.cells[c]?.innerText||'';
    const an=parseFloat(av.replace(/[^0-9.\-]/g,'')), bn=parseFloat(bv.replace(/[^0-9.\-]/g,''));
    if(!isNaN(an)&&!isNaN(bn)) return dir[c]?an-bn:bn-an;
    return dir[c]?av.localeCompare(bv):bv.localeCompare(av);
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
function filter(){{
  const q=document.getElementById('srch').value.toLowerCase();
  document.querySelectorAll('#tb tr').forEach(r=>{{
    r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';
  }});
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# GIT PUSH
# ─────────────────────────────────────────────────────────────────────────────
def git_push():
    ts = datetime.now(IST).strftime("%d-%b %H:%M IST")
    try:
        subprocess.run(["git","add","index.html","prev_results.json"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        subprocess.run(["git","commit","-m", f"📊 screener update — {ts}"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        subprocess.run(["git","push"],
                       cwd=BASE_DIR, check=True, capture_output=True)
        log.info("✅ Pushed to GitHub Pages")
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        # "nothing to commit" is fine
        if "nothing to commit" in err or "nothing added" in err:
            log.info("Git: nothing new to commit")
        else:
            log.error(f"Git push failed: {err}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    now = datetime.now(IST)
    log.info(f"{'='*60}")
    log.info(f"NSE Volume Screener  |  {now.strftime('%d %b %Y  %I:%M %p IST')}")
    log.info(f"{'='*60}")

    if not is_market_open():
        log.info("Market is CLOSED — nothing to do. Exiting.")
        return

    prev_syms = load_prev()
    results   = screen_stocks()
    cur_syms  = {r["symbol"] for r in results}

    # ── Telegram alerts for NEW entries only ──────────────────────────────────
    new_entries = cur_syms - prev_syms
    if new_entries:
        log.info(f"New entries this scan: {new_entries}")
    for r in results:
        if r["symbol"] in new_entries:
            sign = "+" if r["pct"] >= 0 else ""
            msg = (
                f"🚨 <b>Volume Alert | NSE</b>\n"
                f"📈 <b>{r['symbol']}</b>\n"
                f"💰 Price : ₹{r['price']:,.2f} ({sign}{r['pct']}%)\n"
                f"📊 Volume: {r['cur_vol']:,}  (Ratio: {r['ratio']}x avg)\n"
                f"🏢 MCap  : ₹{r['mktcap_cr']:,} Cr\n"
                f"🔗 <a href='https://www.tradingview.com/chart/?symbol=NSE:{r['symbol']}'>TradingView Chart</a>\n"
                f"🕐 {now.strftime('%I:%M %p IST')}"
            )
            send_telegram(msg)
            log.info(f"📱 Telegram sent for {r['symbol']}")

    save_prev(cur_syms)

    # ── Generate dashboard HTML ───────────────────────────────────────────────
    html = generate_html(results, now, len(NS_SYMBOLS))
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    log.info(f"✅ index.html written  ({len(results)} stocks passed)")

    # ── Push to GitHub Pages ──────────────────────────────────────────────────
    git_push()
    log.info("=== Done ===\n")


if __name__ == "__main__":
    main()
