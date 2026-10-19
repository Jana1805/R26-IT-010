# Dataset check — should `madushani_xai` switch datasets?

**Date:** 2026-10-18 · **Viva:** 19–21 Oct 2026 · **Mode:** read-only (no project file changed; analysis ran from the session scratchpad)

**Question:** Should the XAI component keep explaining `load_forecasting_dataset_corrected.csv`, or switch to the dataset Behaviour Intelligence (BI) uses? The goals of a switch would be meaningful explanations and dates that match BI.

**Short answer:**
- BI's dataset gives far more meaningful explanations, and its dates match BI by definition.
- But it has only **2 of the 12 features** (Temperature, Solar Irradiance). Three calendar features can be derived from the timestamp.
- A switch means retraining and regenerating every output, plus UI and README changes. Estimate: **5–8 hours of work at medium-to-high risk**, one day before the viva.
- **Recommendation:** keep the current dataset for the viva demo, and present this check as the identified limitation and next step. Build the BI-dataset version only in **separate files**, and swap it in only if it is finished and tested in time. See §7.

---

## 1. Which dataset does BI use? (confirmed from code)

`behaviour-intelligence/backend/app/core/config.py:11` sets `RAW_DATASET_FILENAME = "synthetic_realistic_load.csv"`. It is loaded by `load_raw_dataset()` (`backend/app/ml/data_loader.py:11-32`), and `pipeline_runner.py:35` and `pipeline_controller.py:33` call that loader.

A third candidate was also checked, because it is the only other file with all 12 XAI features: `electricity-demand-sri-lanka/data/electricity_demand_srilanka_fixed.csv`, used by the neural forecasting component.

| Short name | File |
|---|---|
| **XAI (current)** | `behaviour-intelligence/data/raw/load_forecasting_dataset_corrected.csv` |
| **BI** | `behaviour-intelligence/data/raw/synthetic_realistic_load.csv` |
| **NN** | `electricity-demand-sri-lanka/data/electricity_demand_srilanka_fixed.csv` |

## 2. Structure

| | XAI (current) | BI | NN |
|---|---|---|---|
| Rows | 189,888 | 189,793 | 189,888 |
| Range | 2020-01-01 00:00 → 2025-05-31 23:45 | 2020-01-01 00:00 → **2025-05-31 00:00** | 2020-01-01 00:00 → 2025-05-31 23:45 |
| Frequency | 15 min, 0 gaps, 0 duplicates | 15 min, 0 gaps, 0 duplicates | 15 min, 0 gaps, 0 duplicates |
| Missing values | none | none | none |
| Columns | 15 | **4**: `Timestamp`, `Load Demand (kW)`, `Temperature (°C)`, `Solar Irradiance (W/m²)` | 17 |
| Load mean / std (kW) | 1500.2 / 199.9 | 1747.8 / 349.7 | 1833.4 / 325.2 |
| Load min / max (kW) | 606.9 / 2412.4 | 629.7 / 4365.2 | 850.0 / 2350.0 |
| Of the 12 XAI features | all 12 | **Temperature, Solar Irradiance only** | all 12 |
| Missing XAI features | — | Humidity, Wind Speed, Rainfall, GDP, Per Capita Energy Use, Electricity Price, Public Event; Day of Week, Hour of Day and Month **can be derived from the timestamp** | — |
| Extra columns | `Season` | — | `Unnamed: 0` (index), `Season`, `Poya Day` |
| Calendar columns match timestamp | yes (100%) | n/a (derived) | yes (100%) |

On BI, the analysis below uses 5 features: Temperature, Solar Irradiance, and Day of Week / Hour of Day / Month derived from `Timestamp`.

## 3. Is the target a trivial linear function?

Linear Regression fitted on the full dataset:

| | XAI (current) | BI (5 features) | NN (12 features) |
|---|---|---|---|
| R² | **1.000000** | 0.3451 | 0.0562 |
| Max \|residual\| (kW) | **5.0 × 10⁻⁷** | 2271.0 | 1009.1 |
| Residual std (kW) | 2.3 × 10⁻⁸ | 283.0 | 315.9 |
| Intercept | −1300.000 | 986.92 | 1950.34 |
| Coefficients | **Temperature +100.000**, all 11 others ≈ 0 (\|c\| < 1.5 × 10⁻¹⁰) | Temperature +37.54, Solar −0.544, Day of Week −59.31, Hour +10.03, Month −4.47 | Temp +2.04, Humidity +0.107, Wind +0.557, Rain −0.139, Solar −0.027, GDP −0.025, Per Capita +0.036, Price −0.161, Day of Week −16.09, Hour +0.649, Month −19.21, Public Event −95.34 |
| R², Temperature only | **1.0000** | 0.0240 | 0.0002 |

**Verdict:**
- **XAI (current):** yes, trivial. `Load = 100 × Temperature − 1300` exactly.
- **BI:** no.
- **NN:** no.

### Correlation of each feature with the target (Pearson r)

| Feature | XAI (current) | BI | NN |
|---|---|---|---|
| Temperature | **1.0000** | 0.1550 | 0.0131 |
| Solar Irradiance | 0.0017 | −0.2431 | −0.0043 |
| Day of Week | −0.0005 | −0.3392 | −0.0990 |
| Hour of Day | −0.0026 | 0.3649 | 0.0137 |
| Month | −0.0014 | −0.0450 | −0.2050 |
| Public Event | −0.0050 | — | −0.0641 |
| Humidity / Wind / Rainfall / GDP / Per Capita / Price | all \|r\| ≤ 0.0045 | — | all \|r\| ≤ 0.0043 |

Low linear correlations for hour on BI and NN do not mean "no effect": the hourly shape is a curve (§5).

## 4. Quick model test (chronological 80/20, same preprocessing as notebook 1)

Setup:
- IQR filter on the target, then sort by time, then the first 80% is train and the last 20% is test.
- XGBoost uses the **current best params unchanged**: 467 trees, depth 3, lr 0.0231, subsample 0.925, colsample 0.894, min_child_weight 1, α 0.789, λ 0.466. They were not re-tuned per dataset.
- Two extra baselines:
  - **LR + one-hot calendar**: hour, day-of-week and month as categories, so a linear model can follow the daily and weekly shape.
  - **Seasonal naive**: same 15-minute slot 7 days earlier.

| Dataset (test rows) | Model | RMSE (kW) | MAE (kW) | MAPE | R² |
|---|---|---|---|---|---|
| **XAI (current)** (37,722; 2024-05-01 → 2025-05-31) | Linear Regression | 1.4 × 10⁻⁸ | 7.2 × 10⁻¹⁰ | ≈0% | 1.0000 |
| | LR + one-hot calendar | 1.4 × 10⁻⁸ | 8.4 × 10⁻¹⁰ | ≈0% | 1.0000 |
| | XGBoost | 2.030 | 1.058 | 0.074% | 0.99989 |
| | Seasonal naive | 273.6 | 219.2 | 14.99% | −0.991 |
| **BI** (35,118; 2024-04-28 → 2025-05-31) | Linear Regression | 210.7 | 166.1 | 9.88% | 0.2967 |
| | LR + one-hot calendar | 118.3 | 70.3 | 4.24% | 0.7784 |
| | **XGBoost** | **117.0** | 70.7 | 4.26% | **0.7830** |
| | Seasonal naive | 153.6 | 93.8 | 5.65% | 0.6078 |
| **NN** (37,970; 2024-05-01 → 2025-05-31) | Linear Regression | 407.3 | 359.5 | 16.31% | −2.298 |
| | LR + one-hot calendar | 361.1 | 348.2 | 16.70% | −1.593 |
| | XGBoost | 359.3 | 348.0 | 16.67% | −1.567 |
| | **Seasonal naive** | **88.0** | **61.3** | **3.06%** | **0.846** |

Reading the table:
- **XAI (current):** no model comparison is informative, because LR is exact.
- **BI:** an honest, normal-looking comparison. XGBoost beats plain LR by a wide margin (R² 0.78 vs 0.30) and beats seasonal naive (0.78 vs 0.61). It only ties a linear model that is handed one-hot calendar features. So most of the structure is additive calendar shape, with little interaction left for trees to exploit.
- **NN:** both models fail on the test year. Load has a strong upward trend: yearly means are 1524 (2020), 1668, 1805, 1943, 2068 and 2220 kW (2025), about +140 kW per year. There is no trend, year or lag feature in the 12, and tree models cannot extrapolate beyond the training range. The neural component handles this with 96-step load lags; this XGBoost setup does not.

## 5. Evidence of non-linear and calendar effects

| | XAI (current) | BI | NN |
|---|---|---|---|
| Hourly profile range (max − min of hourly means) | **8.3 kW** (flat) | **915.8 kW**: low about 1,566 at 00–01h, morning bump 1,766 at 08h, **evening peak 2,482 at 19h** | 560.5 kW: low 1,545 at 00h, single midday peak 2,106 at 12h |
| Weekend − weekday (kW) | −0.5 | **−332.2** (Sat/Sun ≈ 1,510 vs Mon–Fri ≈ 1,842) | −153.1 |
| Holiday effect (kW) | Public Event −4.6 | n/a (no holiday column) | Public Event **−95.9**; Poya Day **−214.5** |
| Temperature curve (mean load by 1 °C bin) | perfectly linear, 981 → 2017 kW from 23 → 33 °C | **inverted U**: 1,586 at 21 °C, peak **2,010 at 27 °C**, back to 1,615 at 31 °C | flat: 1,822 → 1,838 kW from 23 → 33 °C |
| Temperature R², linear vs quadratic | 1.0000 / 1.0000 | 0.0240 / **0.1140** | 0.0002 / 0.0002 |
| Temperature slope at hours 03 / 09 / 14 / 19 (kW/°C) | 100.0 / 100.0 / 100.0 / 100.0 | 0.35 / −8.11 / 4.12 / −3.80 | 5.99 / 1.10 / −0.51 / 2.51 |

**BI has clear non-linear structure:** an evening peak, a weekday/weekend step, and a curved temperature response. One caution for the panel: within a fixed hour the temperature slope is near zero. The inverted U is most likely **confounding with time of day** (temperature peaks around midday, load peaks in the evening), not a real cooling or heating effect. BI's data is synthetic, and its provenance is undocumented (already noted in `THESIS_EVIDENCE_IT22545176.md`).

## 6. Quick SHAP (XGBoost above, TreeExplainer, 2,000 random test rows)

| Rank | XAI (current): mean\|SHAP\| kW (share) | BI: mean\|SHAP\| kW (share) | NN: mean\|SHAP\| kW (share) |
|---|---|---|---|
| 1 | Temperature 154.93 (**99.84%**) | Day of Week 118.02 (35.4%) | Hour of Day 185.58 (52.8%) |
| 2 | Solar Irradiance 0.06 (0.04%) | Hour of Day 103.17 (30.9%) | Month 78.19 (22.2%) |
| 3 | Rainfall 0.04 (0.02%) | Month 76.51 (22.9%) | Day of Week 75.53 (21.5%) |
| 4 | Per Capita Energy Use 0.04 (0.02%) | Solar Irradiance 21.42 (6.4%) | Public Event 8.96 (2.6%) |
| 5 | Humidity 0.03 (0.02%) | Temperature 14.46 (4.3%) | Temperature 2.71 (0.8%) |
| Features with > 5% share | **1** | **4** | **3** |

- **XAI (current):** one feature explains everything, which is a property of the data generator rather than a finding.
- **BI:** several meaningful features. SHAP and LIME would have something real to explain, and temporal drift per year would be worth analysing.
- **NN:** calendar features dominate. The 7 weather and economic features are near zero (the largest, Per Capita Energy Use, has a 0.06% share), so the "12 features" are mostly decorative here too.

## 7. Do dates match BI?

Daily load compared across files over 1,978 overlapping days:

| Pair | Corr. of daily mean | Corr. of daily peak | Mean \|peak difference\| |
|---|---|---|---|
| XAI (current) vs BI | **0.0093** | **0.0024** | 637.1 kW |
| NN vs BI | 0.2727 | 0.2070 | 507.2 kW |
| XAI (current) vs NN | 0.1058 | 0.0094 | 226.1 kW |

Example: the daily peak on 2025-01-25 (a BI anomaly day) is **1,894.85 kW in XAI (current)**, **2,951.82 kW in BI** and 2,350.00 kW in NN.

All 60 BI anomaly dates fall inside every file's date range, so `/api/explain-date` returns *something* for each. But in the current setup that something describes a different load series. **Only the BI file makes "explain this BI anomaly day" literally true.**

## 8. Recommendation

| Option | Explanations meaningful? | Dates match BI? | Features | Work / risk before the viva |
|---|---|---|---|---|
| **A. Stay on XAI (current)** | No: 99.8% Temperature by construction | No (r ≈ 0) | 12 (11 inert) | None; already fixed and tested |
| **B. Switch to BI** | **Yes**: 4 features over 5%, realistic errors (MAPE 4.3%) | **Yes** | **5** (2 measured + 3 derived) | 5–8 h; medium–high risk |
| **C. Switch to NN** | Partly: calendar plus holidays meaningful; weather and economic still inert | No (r ≈ 0.2) | 12 + Poya | 6–10 h; high risk (needs trend/lag features or the model fails, R² −1.57) |

**Technically, B is the right target.** It fixes both problems the panel will probe: the trivial linear target and the date mismatch with BI. It also makes the model comparison meaningful: XGBoost 0.783 vs LR 0.297 vs seasonal naive 0.608. The cost is moving from 12 features to 5, which has to be presented honestly.

**For 19–21 Oct, A is safer for the live demo.** It now works correctly after today's fixes. Recommended plan:

1. Demo on A (current, tested).
2. In the presentation, show this check (§3, §5, §6 tables): "the dataset turned out to be a deterministic function of temperature; on BI's dataset the same pipeline gives meaningful, multi-feature explanations". This directly strengthens panel comments 1 and 3.
3. Build B in **separate files**, without overwriting `xgb_model.pkl`, `temporal_drift.json` or `anomaly_diagnosis.json`. Switch the demo only if it is finished and re-tested before the viva.

## 9. Exactly what switching to BI would change

| # | Change | Files | Notes |
|---|---|---|---|
| 1 | New training script (do **not** edit or re-run notebook 1): load BI CSV, derive Hour/Day of Week/Month, choose an outlier policy, chronological 80/20, Optuna re-tune (current params were tuned for a straight line), save model | new `madushani_xai/train_bi_dataset.py` (or `notebooks/3_bi_dataset.ipynb`) → `backend/outputs_bi/xgb_model.pkl` | **Do not apply the current IQR filter.** On BI it removes 14,206 rows (7.5%), 12,228 of them above the upper bound, mostly at 19h (4,984), 20h (3,343) and 18h (2,408), i.e. the evening peaks. It touches **all 60 BI anomaly days**, so the day's maximum reading being explained would be clipped. |
| 2 | Model comparison on the same split: LR, LR + one-hot calendar, Random Forest (tuned or flagged untuned), XGBoost, seasonal naive; RMSE/MAE/MAPE/R²; ideally rolling-origin CV | same script → `outputs_bi/temporal_drift.json["model_comparison"]` | Keep the same JSON schema so the UI table works unchanged |
| 3 | Per-year SHAP drift (5 features) + rankings + insights | same script → `outputs_bi/temporal_drift.json` | 2025 has only Jan–May (and 2025-05-31 has a single reading) |
| 4 | LIME instances | `generate_anomaly_diagnosis.py` (parameterise dataset path, feature list, derived calendar columns, output dir) → `outputs_bi/anomaly_diagnosis.json` | Better: take instances from BI's 60 anomaly days (`behaviour-intelligence/data/processed/anomaly_results.csv`) instead of random draws, so "anomaly diagnosis" is literally true |
| 5 | Backend | `backend/app.py`: `DATASET_CANDIDATES` (BI file), `FEATURE_COLS`/`FEATURE_NAMES` (5 features; derive calendar from `Timestamp`), `OUTPUTS_DIR`/`MODEL_PATH` (→ `outputs_bi`, ideally an env var so A/B can be switched), outlier filter in `load_live_explainer` | `/api/explain-date` logic otherwise unchanged |
| 6 | Temporal Drift UI | `frontend/src/pages/TemporalDrift.jsx` | `DOMINANT_FEATURE = 'Temperature'` and the "Temperature dominates" note must become conditional (no single feature dominates on BI). The comparison note ("LR has almost exactly zero error…") must be rewritten. |
| 7 | LIME UI | `frontend/src/pages/LimeAnomalyDiagnosis.jsx` | Remove the "different dataset from BI" note in the focused view (no longer true). Icons for the 5 features already exist. |
| 8 | Docs | `madushani_xai/README.md`, `MADUSHANI_AUDIT.md`, slides | "12 features" becomes 5; all result numbers change; dataset section rewritten |
| 9 | Verification | — | Re-run endpoint tests, both pages, BI deep link with an anomaly date; check LIME signs and `intercept + Σ = local_pred` again |

**Time estimate (one person who knows the code):**

| Step | Time |
|---|---|
| Steps 1–3 (script + Optuna 50 trials + SHAP) | 2–3 h |
| Step 4 | 0.5–1 h |
| Steps 5–7 | 1–2 h |
| Step 8 | 1 h |
| Step 9 | 0.5–1 h |
| **Total** | **≈ 5–8 h** |

**Main risks:**
- Too little time to re-test before the viva.
- Explaining the drop from 12 features to 5.
- The confounded temperature curve (§5) inviting a question.
- BI's own data being synthetic and of undocumented provenance.
- Any bug in a freshly regenerated output being found live.

Keeping B in separate `outputs_bi/` files (and on a git branch) limits the risk to "not ready", never "demo broken".

---

*Method:* `madushani_xai/experiments/dataset_check.py` (run: `madushani_xai\venv\Scripts\python.exe madushani_xai\experiments\dataset_check.py`). It reads the three CSVs plus the saved model's hyperparameters, and writes only `madushani_xai/backend/outputs/v2/dataset_check.json`. A re-run reproduced every number above exactly (timing fields aside). The run took about 3 s per dataset. No file under `behaviour-intelligence/`, `madushani_xai/` or `electricity-demand-sri-lanka/` was modified.
