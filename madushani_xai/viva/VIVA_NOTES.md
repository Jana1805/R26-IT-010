# Viva notes — XAI component (IT22273062, Madushani R.P.)

**Viva:** 20 Oct 2026 · **Code tag:** `viva-final-candidate` (madushani_xai, branch `main`)

**Sources for every number below:**
- `backend/outputs/v2/*.json`
- `backend/outputs/temporal_drift.json`
- `MADUSHANI_AUDIT.md` and `DATASET_CHECK.md` (workspace root)

Diagrams are in `viva/diagrams/`, figures in `backend/outputs/figures/`, screenshots in `viva/screenshots/`.

---

## 1. Component in one paragraph

- **What it does:** explains an XGBoost electricity-demand model.
  - **Globally (SHAP):** which features drive demand, and whether that changes year to year.
  - **Locally (LIME):** why one 15-minute reading got its prediction, including a live explanation for any historical date sent from the Behaviour Intelligence (BI) dashboard.
- **Pipeline:** dataset → IQR cleaning → chronological split → Optuna-tuned XGBoost → SHAP / LIME → FastAPI (port 8000) → React dashboard with 3 pages (port 5173).
- **BI link:** the BI dashboard (port 3000) links each abnormal day to the LIME page.

Diagram: `viva/diagrams/system_architecture.png`.

---

## 2. Models and methods used

| Model / method | Role | Why chosen | Key parameters (where set) |
|---|---|---|---|
| **XGBoost regressor** | The forecasting model being explained (deployed `backend/outputs/xgb_model.pkl`) | Strong tabular model; **SHAP TreeExplainer computes exact Shapley values for tree models**; trees also capture non-linear effects expected in real metered data | 467 trees · max_depth 3 (≤ 8 leaves) · learning_rate 0.0231 · subsample 0.925 · colsample_bytree 0.894 · min_child_weight 1 · L1 α 0.789 · L2 λ 0.466 · loss `reg:squarederror` · base score 1,500.50 kW · 12 inputs → 1 output · seed 42 (notebook 1, cells 10–12) |
| **Optuna (TPE sampler)** | Hyperparameter search for XGBoost | Bayesian search: more efficient than grid/random search for 8 parameters | 50 trials · seed 42 · objective = RMSE on last 20% of the training period (inner split 120,708 / 30,177) · fitted on a 10,000-row subsample · search space below · best validation RMSE 2.3066 kW |
| **Linear Regression** | Baseline | Simplest model; shows how much structure is linear | sklearn defaults |
| **Random Forest** | Second tree-ensemble baseline | Fair comparison with another tree ensemble | Tuned with the **same Optuna budget** as XGBoost (50 trials, same 10k subsample, same validation split). Space: n_estimators 50–300, max_depth 4–20, min_samples_leaf 1–10, max_features {1.0, 0.7, 0.5, sqrt}. **Best: 191 trees, depth 19, min_samples_leaf 1, max_features 1.0** (val RMSE 0.2365) |
| **Seasonal naive** | "No model" baseline | Standard time-series reference | Prediction = reading at the same 15-min slot 7 days earlier |
| **SHAP TreeExplainer** | Global importance, local attributions, yearly drift | Exact and deterministic for trees; additive (base value + contributions = prediction); has a solid theory (Shapley values) | `tree_path_dependent` mode · base value 1,500.50 kW · drift: SHAP on every row of each year + 20 bootstrap resamples → 95% CI |
| **LIME (LimeTabularExplainer)** | Local explanation of one reading, in plain rules | Model-agnostic and gives human-readable rules ("Temperature > 29.29") | regression mode · background = 2,000 random cleaned rows (seed 42) · QuartileDiscretizer · num_samples 1,000 · num_features 12 · kernel √exp(−d²/σ²), σ = 0.75·√12 ≈ 2.60 · weighted Ridge (α = 1) · real weights read from `local_exp[1]` · random state re-seeded to 42 on every request |
| **IQR outlier filter** | Preprocessing on the target | Removes extreme target spikes before training | 1.5 × IQR; Q1 1,365.22, Q3 1,635.07 → keep 960.45–2,039.84 kW; removes 1,281 rows (0.67%) → 188,607 |
| **Chronological 80/20 split** | Train/test split | Time series: a random split would leak future data into training | train 150,885 rows · test 37,722 rows (2024-05-01 08:00 → 2025-05-31 23:45) |
| **Demand levels** | Labels for LIME instances | Simple, data-driven bands | p25 = 1,366.45 · p75 = 1,634.11 · p90 = 1,753.72 kW (of cleaned data): low < p25 ≤ medium < p75 ≤ high < p90 ≤ peak |
| **Rolling-origin CV** | Robustness of the comparison | Tests every model on several later periods, not one | sklearn `TimeSeriesSplit(n_splits=5)`, expanding window over all 188,607 rows |

**XGBoost Optuna search space (notebook 1, cell 10):**
- n_estimators 100–500
- max_depth 3–8
- learning_rate 0.01–0.30 (log scale)
- subsample 0.6–1.0
- colsample_bytree 0.6–1.0
- min_child_weight 1–10
- reg_alpha 0–1
- reg_lambda 0–1

**Features (12):** Temperature, Humidity, Wind Speed, Rainfall, Solar Irradiance, GDP, Per Capita Energy Use, Electricity Price, Day of Week, Hour of Day, Month, Public Event. There are no lag features and no scaling. Each 15-minute row is predicted on its own.

Diagrams: `xgboost_architecture.png`, `shap_mechanism.png`, `lime_mechanism.png`.

---

## 3. Model comparison

All four models use the same IQR cleaning and the same chronological split. Test set: 37,722 rows (`v2/model_comparison_v2.json`).

| Model | RMSE (kW) | MAE (kW) | MAPE | R² | Train time | Inference / 1,000 rows |
|---|---|---|---|---|---|---|
| Seasonal naive (7 days earlier) | 277.62 | 221.80 | 15.16% | −1.050 | — | 0.05 ms |
| Linear Regression | 1.4 × 10⁻⁸ | 7.2 × 10⁻¹⁰ | ≈ 0% | 1.000000 | 0.07 s | 0.05 ms |
| Random Forest (Optuna-tuned) | 0.0113 | 0.0051 | 0.00035% | 1.000000 | 22.5 s (+43.7 s tuning) | 11.6 ms |
| **XGBoost (deployed)** | **2.0248** | **1.0512** | **0.073%** | **0.99989** | 1.3 s | 0.58 ms |

5-fold rolling-origin CV, RMSE (mean ± std):
- Linear Regression: 1.55 × 10⁻⁸ ± 7.9 × 10⁻¹⁰
- Random Forest: 0.029 ± 0.023
- XGBoost: 2.099 ± 0.066 kW (MAPE 0.076 ± 0.002%, R² 0.999884)

**Interpretation:**
1. **Linear Regression is exact** because in this dataset `Load = 100 × Temperature − 1300`, with a maximum residual of 5 × 10⁻⁷ kW. Accuracy therefore cannot separate the models; any flexible model scores R² ≈ 1.
2. **XGBoost's 2 kW error is the cost of approximating a straight line with 467 shallow trees.** That is 0.07% of mean demand, stable across all 5 CV folds (±0.07 kW), and it predicts 20× faster than Random Forest.
3. **XGBoost is kept for the explanation objective, not for raw accuracy.** It allows exact, fast TreeSHAP. And because the true answer is known, the model can be used to *validate* the explainers (section 4).

---

## 4. XAI comparison: SHAP vs LIME against a known ground truth

**The validation story:**
- The data obeys `Load = 100·T − 1300` exactly, so the *correct* explanation is known: Temperature contributes `100 × (T − mean T)` kW and every other feature contributes 0.
- Normally nobody can check an explainer. Here we can.

All tests run on the deployed model:
- 200 test rows (50 per demand level)
- a 2,000-row SHAP sample
- 30 rows × 10 seeds for LIME stability
- 5 backgrounds for SHAP stability

Source: `v2/xai_comparison.json`.

| Criterion | SHAP TreeExplainer | LIME |
|---|---|---|
| Share of attribution on Temperature (truth: 100%) | **99.90%** | 69.9%, so **~30% spread over 11 irrelevant features** |
| Temperature ranked #1 | 100% | 100% |
| Temperature sign correct | 100% | 100% |
| Match to the true effect `100·(T − mean T)` | **Pearson r = 0.99994, slope 0.999**, intercept −0.004 kW | Not directly comparable (weights are per quartile bin) |
| Fidelity to the model | additivity error max **0.007 kW** | local R² mean 0.46 (low 0.61, **medium 0.06**, high 0.59, peak 0.59); local prediction vs model gap: mean 64 kW, max 264 kW |
| Stability | deterministic; ±0.004 kW across 5 backgrounds (after removing a uniform baseline shift) | Temperature weight std 5.7 kW across 10 seeds; top-1 always the same; **top-3 Jaccard only 0.32** |
| Runtime per explanation | 2.3 ms | 15 ms |
| Agreement | top-1 feature identical in 100% of rows; top-3 overlap 0.44 | (same) |

**Interpretation:**
- **SHAP is provably correct here.** Its Temperature values lie on the true line (r = 0.99994). The remaining 2.1 kW scatter is the model's own approximation error, not SHAP's: the model's test RMSE is also 2.0 kW.
- **LIME finds the right feature, but its weights are less faithful.** It always ranks Temperature first with the right sign, but puts ~30% of its weight on features with zero true effect. Its order of features 2–12 changes with the random seed (top-3 Jaccard 0.32).
- **LIME is weakest for medium demand (R² 0.06).** There, Temperature sits in the two middle quartile bins and a binary "in this bin" surrogate cannot follow a straight line.
- **The two methods disagree beyond rank 1, and that is expected.** Ranks 2–12 are pure noise in both methods (Spearman excluding Temperature = 0.003).
- **Use:** SHAP for trustworthy importance and drift; LIME as a readable, rule-style local explanation, with its R² shown as a confidence indicator in the UI.

Figures:
- `shap_dependence_temperature.png` (visual proof)
- `shap_bar.png`
- `shap_beeswarm.png`
- `lime_example_peak.png` / `lime_example_low.png`
- `lime_stability_box.png`
- `shap_vs_lime_table.png`

### Temporal drift, done properly

The earlier version refitted a new model per year on 2,000 rows and reported "Rainfall biggest gainer, Temperature biggest decline". The v2 method:
- uses **one fixed deployed model**,
- computes SHAP on **every row of each year**,
- draws 20 bootstrap resamples to get a 95% CI,
- flags drift **only when the CIs do not overlap**.

Results:
- Temperature: 156.49 kW (155.50–157.15) in 2020 vs 155.74 kW (154.15–157.36) in 2025 → **not flagged**.
- Rainfall and Temperature (the old headlines) → **not flagged**.
- Only **Month** is flagged (−0.0017 kW, 0.001% of Temperature's importance). That's because 2025 contains only January–May. It is statistically real but practically negligible.
- **Conclusion: no meaningful drift.** This is correct for a fixed, deterministic data generator.

Figure: `temporal_drift_v2.png`.

---

## 5. What changed since PP2, mapped to the panel's comments

| PP2 comment | What was done | Evidence |
|---|---|---|
| **1. "Lacks idea on the models used"** | Full models/methods table with role, reason and settings (section 2). LIME settings documented (discretizer, kernel, samples, background). Clarified that the deployed model differs from the old per-year refits. New dashboard page **03 · Model & XAI Comparison**. README corrected | `viva/VIVA_NOTES.md` §2, `README.md`, page `/model-xai-comparison` |
| **2. "Need a clear idea on the model architecture"** | Five diagrams: system architecture, XGBoost architecture with real hyperparameters (verified from the saved booster: 467 trees, ≤ 8 leaves, base 1,500.50 kW), SHAP mechanism, LIME mechanism, evaluation design | `viva/diagrams/*.png` + `.mmd` source |
| **3. "A model comparison needs to be done"** | Four models with RMSE/MAE/MAPE/R²/train/inference time. Random Forest tuned with the same Optuna budget. Seasonal-naive baseline. 5-fold rolling-origin CV. **SHAP vs LIME comparison against the known ground truth.** Drift with confidence intervals. Cross-dataset check | `experiments/model_and_xai_comparison.py` (seeded, ~3 min), `v2/*.json`, 9 figures, `DATASET_CHECK.md` |

**Bugs found and fixed:**

| Bug | Effect before | Fix |
|---|---|---|
| **LIME sign inverted** | Code read `local_exp[0]`, which LIME fills with the *negated* weights in regression mode. A 32 °C peak day showed Temperature −353 kW | Read `local_exp[1]`; regenerated `anomaly_diagnosis.json`; peak days now +346 to +363 kW, and intercept + contributions = LIME local prediction (±0.0002 kW) |
| **BI deep link showed the wrong day** | XAI searched only the 15 saved samples; 0 of BI's 60 anomaly days matched, so every click showed instance #01 (a low-demand 2022 reading) under a banner claiming it explained the clicked date | `?source=bi&date=` now calls `/api/explain-date` for that date (live LIME); clear "No historical data" message for dates outside the data; accurate banner |
| **LIME randomness in the live endpoint** | The same date gave different weights on each request (e.g. +352 vs +335 kW) | Re-seed LIME's shared RandomState to 42 per request; 3 identical calls verified |
| **Drift was noise** | Per-year refits, no uncertainty | One fixed model + bootstrap CIs; drift flagged only on non-overlap |
| Smaller fixes | Unreadable drift chart (Temperature ~157 kW flattened the other lines); model comparison not shown in the UI; README errors; unpinned requirements; corrupted `.gitignore` | Temperature hidden by default with a note; comparison tables on page 01 and 03; README fixed; requirements pinned; `.gitignore` rewritten |

---

## 6. Honest limitations and future work

**Limitations:**
1. **The dataset is synthetic and exactly linear:** `Load = 100·T − 1300`. The other 11 features have zero effect. Accuracy numbers say nothing about real-world performance, and the "12-feature" story is mostly decorative. *This is also what made the ground-truth validation of SHAP/LIME possible.*
2. **Different dataset from BI.** The XAI component explains `load_forecasting_dataset_corrected.csv`; BI analyses `synthetic_realistic_load.csv`. For the same date the demand differs: 2025-01-25 peak is 1,894.85 kW in XAI vs 2,766 kW on the BI dashboard. Daily peaks correlate at only r = 0.002.
3. **"Anomaly diagnosis" explains readings, it doesn't detect anomalies.** Detection is BI's job (Isolation Forest). The IQR filter even removes the 1,281 most extreme readings before training.
4. **LIME is unstable and has low fidelity for medium demand** (R² 0.06; top-3 Jaccard 0.32 across seeds). Its weights describe quartile bins, not per-unit effects.
5. **shap 0.52 + XGBoost 3.x:** `TreeExplainer` in interventional mode refuses this model ("categorical split not supported"). The background-stability test therefore used shap's model-agnostic `PermutationExplainer`. Also, `xgb_model.pkl` was pickled by an older XGBoost version; it loads and predicts correctly, with a warning.
6. Only XGBoost is explained, not the team's neural models or BI's behaviour labels. There are no lag features. 2025 is a partial year. The drift CIs use only 20 bootstrap resamples. There was no user study of explanation usefulness.

**Future work:**
1. **Switch to BI's dataset** (plan in `DATASET_CHECK.md` §9, estimated 5–8 h). It has real non-linear structure: XGBoost R² 0.783 vs LR 0.297 vs seasonal naive 0.608. SHAP spreads over 4 features (Day of Week 35%, Hour 31%, Month 23%, Solar 6%), and dates would match BI. Needs: no IQR filter (it would remove BI's evening peaks on all 60 anomaly days), Optuna re-tune, regenerated outputs in a separate folder.
2. Add lag/rolling features. Explain the neural models (DeepSHAP / Integrated Gradients). Compare against them on the same data.
3. Stabilise LIME (more samples; average over seeds) or replace it with KernelSHAP / exact TreeSHAP local views.
4. Re-save the model in XGBoost's native JSON format. Use more bootstrap resamples. Run a small user study with energy analysts.

---

## 7. Thirty likely viva questions

**Models and architecture**

1. **Which model do you explain?**
   An XGBoost regressor saved as `xgb_model.pkl`: 467 trees of depth ≤ 3, learning rate 0.0231, trained on 150,885 rows with 12 tabular features. It predicts the load of one 15-minute reading. There are no lags, so each row is predicted on its own.

2. **Why XGBoost if Linear Regression is perfect?**
   Linear Regression is perfect only because this dataset is exactly `100·T − 1300`, so accuracy can't separate the models. XGBoost was chosen for the explanation goal: TreeSHAP gives exact, fast Shapley values for trees, and trees handle the non-linear effects real demand data has. Its error is 2 kW, which is 0.07% of mean demand. LR's coefficients would trivially "explain" this dataset but wouldn't generalise.

3. **Explain the XGBoost architecture.**
   Gradient boosting builds 467 small regression trees one after another. Each new tree is fitted to the remaining error of the ensemble so far, using the gradient and Hessian of the squared-error loss. Prediction = base score (1,500.50 kW) + 0.0231 × the sum of all tree outputs. Regularisation comes from depth ≤ 3, L1 0.789, L2 0.466, and row (0.925) and column (0.894) subsampling.

4. **How were the hyperparameters tuned?**
   Optuna with the TPE (Bayesian) sampler, 50 trials, seed 42. It searched 8 parameters (e.g. depth 3–8, learning rate 0.01–0.3 log-scale) and minimised RMSE on the last 20% of the training period. To keep it fast, each trial trained on a 10,000-row subsample; the final model was then trained on all 150,885 training rows.

5. **Why is the best depth only 3?**
   The target is a straight line in one feature. Shallow trees with many small steps approximate a line well, and deeper trees add nothing. Tuning on a 10k subsample also favours simpler models.

6. **Why a chronological split?**
   This is time-series data. A random split would put future readings into training and leak information, giving over-optimistic scores. The first 80% (to April 2024) trains, and the last 20% (May 2024 → May 2025) tests.

7. **What is rolling-origin cross-validation?**
   The data is cut into 6 consecutive blocks. Fold k trains on everything up to block k and tests on the next block, so every test period is in the future of its training data. We used 5 folds (`TimeSeriesSplit`). XGBoost's RMSE is 2.10 ± 0.07 kW across folds, so the result is stable over time.

8. **Was the comparison fair?**
   Yes. All models used the same cleaning, the same split and the same metrics. Random Forest got exactly the same Optuna budget as XGBoost (50 trials, same subsample, same validation split). A seasonal-naive baseline shows what "no model" achieves (RMSE 277.6 kW).

9. **Why did you remove outliers with IQR?**
   To stop extreme target spikes distorting training. Only 1,281 rows (0.67%) outside 960–2,040 kW were removed. The downside, which I acknowledge, is that the most extreme readings are not explained.

**Explainability**

10. **What is SHAP?**
    SHAP assigns each feature its Shapley value from game theory: its average extra contribution to the prediction over every order in which features could be added. The values add up exactly: base value + sum of contributions = prediction. TreeExplainer computes them exactly for tree models in polynomial time.

11. **What is LIME?**
    LIME explains one prediction by building a simple model around it. It creates 1,000 perturbed versions of the instance (by sampling quartile bins), asks XGBoost to predict them, weights them by closeness, and fits a weighted Ridge regression. The coefficients are the explanation, e.g. "Temperature > 29.29 adds +359 kW".

12. **What is the difference between SHAP and LIME?**
    SHAP has a theoretical guarantee (Shapley axioms, exact additivity) and, for trees, is exact and deterministic. LIME is a local approximation: model-agnostic and gives readable rules, but depends on sampling, binning and kernel width, so it can vary between runs and fit poorly. We use SHAP for global importance and drift, and LIME for readable local explanations.

13. **How do you know SHAP is correct?**
    Because the true effect is known: `Load = 100·T − 1300`. SHAP's Temperature value should be `100 × (T − mean T)`, and on 2,000 test rows it matches with r = 0.99994 and slope 0.999. It puts 99.90% of attribution on Temperature (truth: 100%), and base + contributions equals the prediction within 0.007 kW.

14. **Why is LIME's R² low for medium demand?**
    LIME turns Temperature into four quartile bins. A medium-demand reading sits in one of the two middle bins, and moving in either direction changes demand in opposite ways, so a binary "in this bin or not" feature can't capture it. The local linear fit explains only ~6% of the variation (R² 0.06), versus ~0.6 at low/high/peak.

15. **LIME puts weight on irrelevant features. Is that a bug?**
    No, it's a known LIME property: sampling noise and the Ridge fit spread ~30% of the weight over features with zero true effect. That is exactly why we measured it against the ground truth. LIME still ranks Temperature first with the correct sign in 100% of 200 instances.

16. **Are your explanations stable?**
    SHAP is deterministic: same input, same answer. Across 5 different backgrounds it varies by only ±0.004 kW after removing a uniform baseline shift. LIME's Temperature weight varies by about 5.7 kW (1.6%) across 10 seeds and its top feature never changes, but its features 2–3 change (top-3 Jaccard 0.32). The live endpoint fixes the seed, so a given date always returns the same explanation.

17. **What does "mean |SHAP| = 157 kW" mean?**
    On average, Temperature moves a prediction 157 kW away from the base value of 1,500.5 kW. It equals 100 kW/°C × the average distance of temperature from its mean (about 1.57 °C).

18. **What is temporal drift, and did you find any?**
    Drift is a change over time in how strongly a feature drives the predictions. With one fixed model and 95% bootstrap confidence intervals per year, no feature that matters drifted: Temperature stays at 155.7–156.8 kW in every year, with overlapping CIs. Only Month is flagged, by 0.0017 kW, because 2025 covers only January–May. The earlier "Rainfall is rising" claim was noise and is not flagged.

19. **Why did you redo the drift analysis?**
    The old method refitted a separate model per year on 2,000 rows, so year-to-year differences mixed data changes with model randomness, and there was no uncertainty estimate. Using one model and confidence intervals separates real change from noise.

20. **Why does a peak day show "Temperature > 29.29: +359 kW"?**
    LIME found that being in the top temperature quartile (> 29.29 °C) raises the prediction by about 359 kW relative to its local baseline. That agrees with the data: hotter means more demand, at 100 kW per °C.

21. **You had a sign bug. What was it?**
    In regression mode LIME stores the real weights under key 1 and a negated copy under key 0, and our code read key 0. Every weight was flipped, so hot days looked like they *reduced* demand. We now read `local_exp[1]`, regenerated the outputs, and verified that intercept + contributions equals LIME's local prediction.

**System, data and integration**

22. **Is your dataset real?**
    No. Its target is exactly `100 × Temperature − 1300` (maximum residual 5 × 10⁻⁷ kW), so it is synthetic, and its origin isn't documented. We say this openly: it limits what accuracy means, but it gives a known ground truth that let us validate SHAP and LIME.

23. **Where is the anomaly detection?**
    Anomaly detection is in Behaviour Intelligence (Isolation Forest on daily profiles). This component *diagnoses*: when BI flags a day, its "LIME →" button opens our page, which explains the model's prediction for that day's highest-demand reading. We don't claim to detect anomalies ourselves.

24. **How does it integrate with the other components?**
    BI's abnormal-day table links to `http://localhost:5173/anomaly-diagnosis?source=bi&date=YYYY-MM-DD`. Our page calls `/api/explain-date` and shows a live LIME explanation. The XAI backend reads its dataset from `behaviour-intelligence/data/raw/`, and all four components start together with `start-all.py`. There is no link to the neural forecasting models.

25. **Why are the demand values on your page different from BI's for the same date?**
    The two components use different dataset files. For 2025-01-25, BI shows a 2,766 kW peak and our dataset has 1,894.85 kW. The page says this explicitly. The fix is to retrain on BI's dataset; we analysed it (`DATASET_CHECK.md`) and estimate 5–8 hours.

26. **What happens if BI sends a future date?**
    `/api/explain-date` returns 404 because there are no feature values to explain, and the page says "No historical data for this date" instead of showing an unrelated example. Invalid dates return 422.

27. **What are the API endpoints?**
    - `/api/temporal-drift`
    - `/api/anomaly-diagnosis` (15 saved instances)
    - `/api/explain-date?date=` (live LIME)
    - `/api/v2/model-comparison`, `/api/v2/xai-comparison`, `/api/v2/temporal-drift`
    - `/api/figures/*.png`

    All are FastAPI on port 8000, documented at `/docs`.

28. **Is the work reproducible?**
    Yes. `experiments/model_and_xai_comparison.py` uses fixed seeds and runs in about 3 minutes; two full runs gave identical results apart from timings. `generate_anomaly_diagnosis.py` regenerates the LIME file exactly. Requirements are pinned, and the deployed model and original outputs are backed up.

29. **Why not use deep learning or explain the team's neural models?**
    This component focused on validating explanation methods on a tree model, where exact SHAP exists. Explaining the CNN/LSTM/Transformer forecasters would need DeepSHAP or Integrated Gradients and a shared dataset. That is listed as future work.

30. **What would you do with more time?**
    - Retrain and re-explain on BI's dataset, where several features genuinely matter (SHAP spread 35/31/23/6%) and dates match BI.
    - Add lag features.
    - Stabilise LIME or replace it with KernelSHAP.
    - Run a small user study to check that the explanations help analysts.
