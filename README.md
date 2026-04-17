# 📊 NSE Volume Gainers — GitHub Actions Automation

> Scans NSE 500 stocks every **15 minutes** during market hours (Mon–Fri, 9:30 AM – 3:15 PM IST).
> Reports are saved as CSVs and browsable via a GitHub Pages website.

---

## 📁 Repository Structure

```
your-repo/
│
├── volume_gainers.py       ← Scanner script (modified)
├── generate_index.py       ← Rebuilds index.html after each scan
├── requirements.txt        ← Python dependencies
├── index.html              ← GitHub Pages download hub (auto-updated)
├── nse500list.csv          ← ⚠ YOU MUST ADD THIS FILE
│
├── reports/                ← Auto-created; CSVs saved here
│   ├── 2025-06-10_09-30.csv
│   ├── 2025-06-10_09-45.csv
│   └── ...
│
└── .github/
    └── workflows/
        └── volume_gainers.yml   ← GitHub Actions schedule
```

---

## 🚀 Step-by-Step Setup

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) → **New repository**
2. Name it e.g. `nse-volume-gainers`
3. Set it to **Public** (required for free GitHub Pages)
4. Click **Create repository**

---

### Step 2 — Upload your files

Upload these files to the **root** of your repository:

| File | Notes |
|------|-------|
| `volume_gainers.py` | The modified scanner |
| `generate_index.py` | Rebuilds the HTML report page |
| `requirements.txt` | pip dependencies |
| `index.html` | Initial placeholder page |
| `nse500list.csv` | **Your NSE 500 stock list** — must have a `Symbol` column |

> To upload: Go to your repo → **Add file** → **Upload files**

---

### Step 3 — Create the workflow file

1. In your repo, click **Add file** → **Create new file**
2. Type the filename as: `.github/workflows/volume_gainers.yml`
   (GitHub will auto-create the folders)
3. Paste the contents of `volume_gainers.yml` and commit.

---

### Step 4 — Enable GitHub Actions write permissions

1. Go to your repo → **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

---

### Step 5 — Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Branch: `main` | Folder: `/ (root)`
4. Click **Save**
5. Your site will be live at:
   `https://<your-username>.github.io/<repo-name>/`

---

### Step 6 — Test with a manual run

1. Go to **Actions** tab → **NSE Volume Gainers — 15-min Scanner**
2. Click **Run workflow** → **Run workflow**
3. Watch the run complete (~2–3 min)
4. Check the `reports/` folder — a new CSV should appear
5. Visit your GitHub Pages URL to see the download hub

---

## ⏰ Schedule Details

| IST Time | UTC Time (cron) |
|----------|----------------|
| 9:30 AM  | 4:00 AM |
| 9:45 AM  | 4:15 AM |
| 10:00 AM | 4:30 AM |
| …        | … |
| 3:00 PM  | 9:30 AM |
| 3:15 PM  | 9:45 AM |

Cron expression: `0,15,30,45 4-9 * * 1-5`

> **Note:** GitHub Actions cron can have a delay of up to ~5 minutes.

---

## 📋 CSV Report Columns

| Column | Description |
|--------|-------------|
| Ticker | NSE symbol |
| Current Price (₹) | Last traded price |
| Prev Close (₹) | Previous day's close |
| Gain % | % move from prev close |
| Volume | Today's volume |
| 10D Avg Volume | 10-day average volume |
| Vol Surge (x) | Volume / 10D avg (e.g. 2.3x) |
| Scan Time (IST) | When this scan ran |

---

## 🛠 Troubleshooting

| Problem | Fix |
|---------|-----|
| Workflow doesn't trigger | Check Actions → General → Read & Write permissions |
| `nse500list.csv` not found | Ensure it's in the repo root with a `Symbol` column |
| Pages not updating | Wait 2–3 min after workflow completes |
| No stocks found | Market may be closed or no stocks met the 1.5× volume criteria |
