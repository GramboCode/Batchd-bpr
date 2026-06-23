# BatchD BPR Module — Deployment Guide

## Architecture Overview

```
BatchD (GAS web app)
  └── "Open BPR" button ─────────────────────────────────────────┐
                                                                    ↓
                                              Railway BPR Frontend (React)
                                                    │  URL params: uid, product, batchId, mfgDate
                                                    ↓
                                              Railway BPR Backend (FastAPI)
                                                    │  Postgres: bpr_records, bpr_phase_signoffs, bpr_step_checks
                                                    │
                              ┌─────────────────────┼──────────────────────────┐
                              ↓                     ↓                          ↓
                    Phase sign-offs           PDF generation              GAS webhook
                    (real-time steps)         (reportlab)                 (BPR_STATUS update)
                                                    ↓
                                              Google Drive
                                              (UID subfolder)
```

## Step 1 — Railway Backend Setup

1. In your existing Railway project (same as ManifestD), create a new service:
   - Source: this repo's `/backend` directory
   - Start command: `uvicorn bpr_api:app --host 0.0.0.0 --port $PORT`

2. Copy `bpr_phases.py` to the same directory as `bpr_api.py` on Railway.

3. Set these environment variables in Railway:
   ```
   DATABASE_URL           = (already set from ManifestD Postgres)
   GAS_WEBHOOK_URL        = https://script.google.com/a/macros/punchedibles.com/s/YOUR_DEPLOYMENT_ID/exec
   GOOGLE_SERVICE_ACCOUNT = (paste the JSON of your Google service account)
   DRIVE_COA_FOLDER_ID    = (the COA Archive root folder ID)
   ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Note your Railway service URL (e.g., `https://batchd-bpr-production.railway.app`)

## Step 2 — Frontend Setup (Railway or Netlify)

### Option A: Railway (same project, simplest)
1. Create another Railway service from `/frontend`
2. Build command: `npm run build`
3. Start command: `npx serve dist -p $PORT`
4. Set env var: `VITE_API_URL=https://your-bpr-backend.railway.app`

### Option B: Netlify
1. Connect `/frontend` directory to Netlify
2. Build command: `npm run build`
3. Publish directory: `dist`
4. Set env var in Netlify dashboard: `VITE_API_URL=https://your-bpr-backend.railway.app`

## Step 3 — GAS Setup

1. Open your GAS Punch Tools project in the Apps Script editor.

2. Add to `AConfig.gs` inside the `CONFIG.COL` object:
   ```javascript
   STICKERED_QTY: 14,  // already there
   BPR_STATUS:    36,  // NEW — col AJ
   BPR_PDF_URL:   37,  // NEW — col AK (optional, for storing PDF Drive URL)
   ```

3. Add new constant below CONFIG:
   ```javascript
   const BPR_APP_URL = "https://your-frontend-url.railway.app"; // or Netlify URL
   ```

4. Create a new file `BPR.gs` and paste the contents of `gas_additions.js`.

5. Add to `batch.html`:
   - Add the "Open BPR" button to the Label card (see comments in gas_additions.js)
   - Add the BPR JS functions to the script block
   - Add `loadBPRStatus(batch.metrcUID)` at end of `onBatchLoaded()`

6. Add to the `onOpen()` menu in `AConfig.gs`:
   ```javascript
   .addSeparator()
   .addItem('Show BPR QR Code', 'showBPRQRSidebar')
   ```

7. **IMPORTANT**: Make sure your GAS web app deployment is:
   - Execute as: **Me**
   - Who has access: **Anyone** (so Railway can POST to the webhook)
   - Re-deploy after adding doPost()

## Step 4 — Google Drive Service Account (for PDF upload)

If you already have a service account from ManifestD, reuse it:
1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Download the JSON key for your existing service account
3. Share the COA Archive Google Drive folder with the service account email
   (give it "Editor" access so it can create files)
4. Paste the entire JSON as the `GOOGLE_SERVICE_ACCOUNT` env var in Railway

## Step 5 — Test the flow

1. Open BatchD → find any batch → batch detail page
2. "Open BPR" button should now appear in the Label card
3. Click it → Railway BPR app opens with batch context pre-filled
4. Set your name → work through phases → sign off each phase
5. Supervisor release → PDF generated → check UID folder in Google Drive
6. Return to BatchD batch detail → BPR status should show "completed"

## URL Structure

Employee access (phone/tablet via QR code or direct link):
```
https://your-bpr-frontend.railway.app/bpr?uid=METRC_UID&product=Product+Name&batchId=BATCH-001&mfgDate=2026-06-20
```

QR codes encode this URL. Generate from the GAS sheet via
🥊 Punch Tools → Show BPR QR Code (select a row first).

## Employee Identity

- Employees type their name once on first use — it's saved to localStorage on their device
- No login required for production floor access
- Future: swap name input for employee number lookup against KiDa HR Pro roster
- The name field in the database stays the same — just the input method changes

## Phase Structures Built (Phase 1)

| Product Family | BPR Key | Phases |
|---|---|---|
| Live Rosin Concentrate | `live_rosin` | 7 phases |
| Gummies / Fruit Snacks | `gummies` | 8 phases |
| Vape Carts / AIO | `vapes` | 7 phases |
| BHO Badder / Shatter | `bho_badder` | 7 phases |

## Adding New Product Families

Add to `bpr_phases.py` BPR_PHASES dict, then add a detection rule in `detect_product_family()`.
No frontend changes needed — the React app reads phase definitions from the API dynamically.

## Known Limitations / Phase 2

- PDF generation requires reportlab + google-api-python-client on Railway (both in requirements.txt)
- Concurrent writes are handled by Postgres row-level locking — no GAS concurrency issues
- The GAS webhook is fire-and-forget (Railway won't retry if GAS is temporarily down)
- Dr. Norm's and LiquidAbs product families to be added in Phase 2
