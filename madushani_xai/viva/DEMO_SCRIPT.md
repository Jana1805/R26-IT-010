# Demo script — 10 minutes

The live demo runs on the workspace root `D:\Y4S1\Research\Component1-Behaviour-Intelligence`. The backup screenshots are in `madushani_xai\viva\screenshots\`.

## Before the viva (morning, ~2 minutes)

1. Open a terminal in the workspace root and run:
   ```
   powershell -ExecutionPolicy Bypass -File madushani_xai\viva\preflight.ps1
   ```
   It starts the system in a new window (unless it is already running), then checks 29 things. Expect **`ALL 29 CHECKS PASSED`**. Leave the `start-all.py` window open.
2. Open these browser tabs in advance, in this order:
   1. `http://localhost:3000`
   2. `http://localhost:5173/temporal-drift`
   3. `http://127.0.0.1:8000/docs`
3. Close other apps. Set zoom to 100% (or 110% for a projector).
4. If anything fails, see **Backup plan** at the bottom.

## Live demo (10:00)

| Time | Screen / action | What to say |
|---|---|---|
| **0:00** | Terminal: show the running `start-all.py` window (or run `python start-all.py` now; it takes about 10 s). Point at the 4 `START …-backend` lines and the 4 frontend URLs. | "The whole system starts with one command. Four components, each with its own backend and Python environment. Mine is the XAI component: backend on 8000, dashboard on 5173." |
| **0:40** | Terminal: `powershell -ExecutionPolicy Bypass -File madushani_xai\viva\preflight.ps1 -NoStart` → scroll to `ALL 29 CHECKS PASSED`. | "This health check calls every endpoint, every figure and the integration link. Everything passes." |
| **1:20** | Tab `localhost:3000` (BI dashboard). Scroll to **Recent abnormal days**. Point at the **2025-01-25** row (peak 2,766 kW, High risk). | "This is my teammate's Behaviour Intelligence dashboard. It flagged 25 January 2025 as an abnormal day. Each row has a LIME button." |
| **1:50** | Click **LIME →** on the 2025-01-25 row. A new tab opens: `localhost:5173/anomaly-diagnosis?source=bi&date=2025-01-25`. | "The button opens my component for exactly that date, and my backend computes a fresh LIME explanation." |
| **2:10** | On the live page, point to: the banner; Actual 1,894.85 / XGB predicted 1,894.24 kW (error −0.62); the R² bar 0.589; the top bar **Temperature > 29.29 → +359.20 kW**. | "It explains the day's highest-demand reading, at 10:45. The model is almost exact here. LIME says the main reason is temperature above 29.3 °C, adding about 359 kW. The other bars are small. The R² of 0.59 is LIME's own fit quality, so we show it as a confidence bar." |
| **2:50** | Point to the intercept 1,399.34 kW and local prediction 1,794.06 kW; then the grey note at the bottom. Press **F5** once. | "Intercept plus contributions gives LIME's local prediction. Honest note: this dataset differs from BI's file, so BI shows 2,766 kW and we show 1,895 kW for the same date. Fixing that is my next step. And if I refresh, the numbers are identical: the explanation is deterministic." |
| **3:30** | Tab `localhost:5173/temporal-drift` (page **01**). Point at the KPI cards and the red **"Temperature dominates"** note. Click the **Temperature** toggle on, then off. | "Page one is SHAP. Temperature's importance is about 157 kW; no other feature reaches 0.3. With it switched on, everything else is flat, which is why it's hidden by default." |
| **4:15** | Scroll down to **Forecasting Model Comparison**. | "Here's the comparison against Linear Regression and Random Forest. Linear Regression is exact because this synthetic data is 100 × temperature − 1300. I'll come back to why that's useful." |
| **4:45** | Sidebar → **02 LIME Anomaly Diagnosis**. Click filter **Peak**, select **#15** (Temperature > 29.29, +353.38 kW). Then filter **Medium**, select **#04** (R² 0.04). | "These are 15 saved examples across demand levels. Peak days: temperature in the top bin pushes demand up. Medium demand: LIME's fit is weak, R² 0.04, because a linear model on quartile bins can't follow the middle of the range. The page warns about this." |
| **5:45** | Sidebar → **03 Model & XAI Comparison**. Read the red intro box aloud (one sentence). | "Because we know the true formula, we can check whether SHAP and LIME are right instead of trusting them." |
| **6:15** | Scroll: forecasting table → **5-fold rolling-origin CV** table. | "All four models, same split, same metrics; Random Forest got the same tuning budget. XGBoost: 2.02 kW error, 0.07%, stable across five time folds." |
| **7:00** | Scroll to section **B**: the SHAP-vs-LIME table, then the **dependence plot** (dots on the orange line). | "This is the key evidence. SHAP's Temperature values lie exactly on the true effect: r = 0.99994, slope 0.999. SHAP puts 99.9% of importance on Temperature, which is correct. LIME also ranks Temperature first every time, but spreads about 30% onto irrelevant features." |
| **7:50** | Scroll to the **LIME stability** box plot, then section **C** drift panels + table. | "Across 10 random seeds LIME's main weight moves by about 6 kW, and its second and third features change. For drift: one fixed model, bootstrap confidence intervals. No meaningful drift. Only Month is flagged, by 0.002 kW, because 2025 has only five months." |
| **8:40** | Tab `127.0.0.1:8000/docs` (Swagger). Expand **GET /api/explain-date** → *Try it out* → date `2025-01-25` → **Execute** (200, JSON with `"rule": "Temperature > 29.29"`). Then `2026-10-20` → **Execute** (404). | "Everything on screen comes from this documented API. Here is the same live explanation as JSON. A future date returns 404, and the dashboard turns that into a clear message." |
| **9:30** | Back to page **03** top. | "In summary: the models and architecture are documented, both the models and the explanation methods are compared with real metrics, and SHAP is proven correct against the ground truth. Thank you." |
| **10:00** | End. | |

**Do not** click into the "Explainable AI" iframe in the BI sidebar during the demo. Use the direct tabs; they are faster and larger.

## Backup plan

| Problem | Quick fix (≤ 1 min) | If still broken |
|---|---|---|
| `start-all.py` prints `SKIP …: python not found` | That component's venv is missing. For BI: `behaviour-intelligence\.venv`; for XAI: `madushani_xai\venv` | Show the screenshots |
| `Errno 10048` / "port in use" | Another copy is already running. Use it (preflight `-NoStart`) or close it: `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F` | Restart the laptop's terminal and run `python start-all.py` again |
| XAI pages show "Could not load data" | Backend 8000 is down. In `madushani_xai\backend`: `..\venv\Scripts\python.exe -m uvicorn app:app --port 8000` | Screenshots `01`–`05` |
| XAI dashboard not loading | In `madushani_xai\frontend`: `npm run dev` | Screenshots |
| BI dashboard down | In `behaviour-intelligence\backend`: `..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001`; in `behaviour-intelligence\frontend`: `npm run dev` | Open the deep link directly: `http://localhost:5173/anomaly-diagnosis?source=bi&date=2025-01-25`, then use screenshot `07` to show the button |
| Live page says "No historical data" | Check the URL date is `2025-01-25` | Screenshot `03` |
| Figures missing on page 03 | Check `http://127.0.0.1:8000/api/figures/shap_bar.png` | PNGs in `madushani_xai\backend\outputs\figures\` |
| A warning about "older version of XGBoost" in the backend window | Harmless: the pickled model loads and predicts correctly | — |
| No internet | Everything runs locally; only web fonts fall back to system fonts | — |

**Backup screenshots** (`madushani_xai\viva\screenshots\`), in demo order:

| File | Shows |
|---|---|
| `06_bi_dashboard.png` | BI dashboard |
| `07_bi_lime_button_row_2025-01-25.png` | Abnormal-days table with the 2025-01-25 row and LIME buttons |
| `03_xai_lime_live_2025-01-25.png` | Live LIME explanation for 2025-01-25 |
| `01a_xai_temporal_drift_top.png` / `01_xai_temporal_drift.png` | Page 01 (top / full page) |
| `02_xai_lime_list.png` | Page 02 |
| `04a_xai_model_xai_comparison_top.png` / `04_xai_model_xai_comparison.png` | Page 03 (top / full page) |
| `05_xai_swagger_docs.png` | Swagger API docs |

Re-capture them at any time (system running): `node madushani_xai\viva\tools\capture_screenshots.mjs`.

## After the demo

Press **Ctrl+C** in the `start-all.py` window. It stops all four components.
