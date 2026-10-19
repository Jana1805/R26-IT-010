# Slides — XAI component (IT22273062) · 10 minutes · 12 slides

Timing is about 50 s per slide. Paths are relative to `madushani_xai/`: figures in `backend/outputs/figures/`, diagrams in `viva/diagrams/`, screenshots in `viva/screenshots/`.

---

## 1. Explainable AI for Electricity Demand Intelligence

- Component 4 of R26-IT-010 · Madushani R.P. · IT22273062 · Supervisor: Dr. Nathali Silva
- SHAP and LIME explanations for an XGBoost demand model
- Validated against a known ground truth; linked to the Behaviour Intelligence dashboard

**Visual:** `viva/screenshots/04a_xai_model_xai_comparison_top.png` (cropped) as background.

**Speaker notes (45 s):** "Good morning. My component makes the demand-forecasting model explainable. It answers two questions: which factors drive electricity demand, and why did the model predict this value for this moment? I'll cover the models and their architecture, the model comparison and the explanation-method comparison the panel asked for at PP2, and then show it working live with the Behaviour Intelligence dashboard."

---

## 2. Problem

- ML demand forecasts are accurate but opaque: operators can't see *why*
- Without reasons, high-stakes energy decisions can't trust or audit a model
- Explanation methods disagree and can be wrong, so they must be **validated**, not just shown
- Behaviour Intelligence flags abnormal days, but doesn't say what drove the demand

**Visual:** none, or a simple "black box → ?" icon.

**Speaker notes (50 s):** "Forecasting models give numbers without reasons. For an energy planner that's a trust problem. If the model says tomorrow's peak is high, they need to know whether that's temperature, a holiday or something else. Explanation methods like SHAP and LIME exist, but they are approximations and can disagree, so presenting their output is not enough; we need evidence they are correct. Finally, my teammate's Behaviour Intelligence component detects abnormal days, and my component explains them."

---

## 3. Objectives

- Explain a tuned XGBoost demand model globally (SHAP) and locally (LIME)
- Compare forecasting models fairly, and compare SHAP vs LIME on measurable criteria
- Detect temporal drift in feature importance with statistical confidence
- Serve everything through an API and dashboard, integrated with Behaviour Intelligence

**Visual:** none.

**Speaker notes (40 s):** "My objectives were: build and tune the model; explain it globally with SHAP and per prediction with LIME; compare both the models and the explanation methods with real metrics; check whether feature importance drifts over the years; and deliver it as a working system linked to the other components."

---

## 4. System architecture

- Dataset (189,888 rows, 15-min, 2020–2025) → IQR cleaning → chronological 80/20 split
- Optuna-tuned XGBoost → SHAP (global + per-year drift with CIs) and LIME (saved + live per date)
- FastAPI backend (port 8000) → React dashboard with 3 pages (port 5173)
- BI dashboard (port 3000) "LIME →" button → live explanation for that date

**Visual:** `viva/diagrams/system_architecture.png`.

**Speaker notes (60 s):** "This is the end-to-end pipeline. The data is 15-minute readings with 12 features: weather, economic and calendar. I remove extreme target values with the IQR rule, 0.67% of rows, and split chronologically so the test set is the most recent year. Optuna tunes XGBoost. The model is explained in two ways: SHAP for global importance and yearly drift, and LIME for individual readings, including a live explanation for any date. A FastAPI backend serves the results, and the React dashboard has three pages. When Behaviour Intelligence flags an abnormal day, its LIME button opens my page for that date."

---

## 5. Models and methods used (PP2 comment 1)

| | Role | Key settings |
|---|---|---|
| XGBoost | model explained | 467 trees, depth 3, Optuna 50 trials |
| Linear Regression / Random Forest / seasonal naive | baselines | RF tuned with the same Optuna budget |
| SHAP TreeExplainer | global + drift | exact, base value 1,500.5 kW |
| LIME | local rules | 1,000 samples, quartile bins, 2,000-row background, seed 42 |

**Visual:** this table, plus `viva/diagrams/shap_mechanism.png` and `lime_mechanism.png` side by side (small).

**Speaker notes (60 s):** "At PP2 the panel said I lacked clarity on the models, so here is the full list. XGBoost is the model being explained. Linear Regression, a tuned Random Forest and a seasonal-naive baseline are comparators. SHAP assigns each feature its Shapley value, its average contribution over all feature orderings, and for trees it is exact. LIME explains one prediction by perturbing it a thousand times, weighting nearby samples and fitting a small weighted linear model. The settings are documented and fixed, so results are reproducible."

---

## 6. XGBoost architecture (PP2 comment 2)

- 12 inputs → 467 boosted regression trees (depth ≤ 3, ≤ 8 leaves) → 1 output (kW)
- Prediction = base score 1,500.50 kW + 0.0231 × Σ tree outputs
- Each tree fits the remaining error using the gradient + Hessian of the squared-error loss
- Regularisation: L1 0.789 · L2 0.466 · row subsample 0.925 · column subsample 0.894
- Tuned by Optuna TPE: 50 trials over 8 parameters, validation RMSE 2.31 kW

**Visual:** `viva/diagrams/xgboost_architecture.png`.

**Speaker notes (60 s):** "XGBoost is gradient boosting. It starts from the average demand, 1,500.5 kW, then adds 467 small trees one after another. Each tree is fitted to the mistakes the previous trees left, using first- and second-order gradients of the squared error. Each tree's output is scaled by the learning rate, 0.023, and summed. The trees are at most three levels deep, and L1/L2 penalties plus row and column subsampling prevent overfitting. These values were found by Optuna's Bayesian search over 50 trials; I read them back from the saved model to confirm."

---

## 7. Model comparison (PP2 comment 3)

| Model | RMSE (kW) | MAPE | R² | Inference / 1k rows |
|---|---|---|---|---|
| Seasonal naive | 277.6 | 15.2% | −1.05 | 0.05 ms |
| Linear Regression | 1.4e-8 | ≈0% | 1.000 | 0.05 ms |
| Random Forest (tuned) | 0.011 | 0.0004% | 1.000 | 11.6 ms |
| **XGBoost** | **2.02** | **0.07%** | **0.99989** | 0.58 ms |

- 5-fold rolling-origin CV: XGBoost 2.10 ± 0.07 kW, stable across time
- LR is exact because the data is **Load = 100 × Temperature − 1300**

**Visual:** `backend/outputs/figures/model_comparison_rmse_mape.png`.

**Speaker notes (60 s):** "All models use the same cleaning, the same chronological split and the same metrics; Random Forest got the same tuning budget as XGBoost. Linear Regression is essentially perfect, and I'll be honest about why: this dataset is synthetic, and demand is exactly 100 times temperature minus 1300. So accuracy can't separate the models. XGBoost's 2 kW error is 0.07% of demand and is stable across five rolling folds. I keep XGBoost for the explanation goal: exact TreeSHAP. And the known formula becomes an advantage on the next slides."

---

## 8. SHAP results

- 99.90% of attribution goes to Temperature, matching the truth (the other 11 features have zero effect)
- SHAP Temperature value vs true effect 100·(T − mean T): **r = 0.99994, slope 0.999**
- Additivity: base + contributions = prediction within 0.007 kW
- Drift with 95% bootstrap CIs: no meaningful drift (Temperature 155.7–156.8 kW every year)

**Visual:** `backend/outputs/figures/shap_dependence_temperature.png` (main), `shap_beeswarm.png` (small).

**Speaker notes (60 s):** "Because the true formula is known, I can check SHAP against the right answer. The scatter shows SHAP's value for Temperature on every test row, with the true line on top: they coincide, correlation 0.99994, slope 0.999. SHAP gives 99.9% of importance to Temperature, which is correct. For drift, I now use the one deployed model, every row of each year, and bootstrap confidence intervals. Nothing important drifts, which is right for this data. The earlier 'Rainfall is rising' finding disappears: it was noise."

---

## 9. LIME results

- Live explanation for 2025-01-25 10:45: **Temperature > 29.29 → +359 kW**, R² 0.59
- Temperature ranked #1 with the correct sign for 100% of 200 test instances
- Fit depends on demand level: R² ≈ 0.6 for low/high/peak, but **0.06 for medium**
- Same date → same answer (fixed seed); a sign bug and a wrong-day deep link were found and fixed

**Visual:** `backend/outputs/figures/lime_example_peak.png` and `lime_example_low.png`, or `viva/screenshots/03_xai_lime_live_2025-01-25.png`.

**Speaker notes (55 s):** "LIME gives a readable rule: on this peak day, being above 29.3 degrees added about 359 kW. On 200 test instances it always picks Temperature first with the right direction. But its local fit is weak for medium demand. There, temperature sits in the two middle bins, which a 'this bin or not' model can't follow, so the dashboard shows R² as a confidence bar. During the audit I found that the code read LIME's negated weights, so hot days looked like they reduced demand. That is fixed and verified."

---

## 10. SHAP vs LIME comparison

| | SHAP | LIME |
|---|---|---|
| Attribution on true feature | 99.90% | 69.9% (~30% on irrelevant features) |
| Fidelity | error ≤ 0.007 kW | R² 0.46 mean, 0.06 for medium |
| Stability | deterministic | Temperature weight ±5.7 kW; top-3 Jaccard 0.32 |
| Runtime | 2.3 ms | 15 ms |
| Agreement | same top-1 feature 100% | top-3 overlap 0.44 |

**Visual:** `backend/outputs/figures/shap_vs_lime_table.png` + `lime_stability_box.png`.

**Speaker notes (55 s):** "This is the explanation-method comparison. Against the ground truth, SHAP is exact, faster and deterministic. LIME gets the main driver right every time, but spreads about 30% of its weight over features that truly have no effect, and its ranking beyond the first feature changes with the random seed. Ranks two to twelve disagree between the methods, as they should: those features are noise. My conclusion: use SHAP for trustworthy importance, and LIME as a readable local summary with its confidence shown."

---

## 11. Integration with Behaviour Intelligence

- BI dashboard abnormal-day row → "LIME →" → `localhost:5173/anomaly-diagnosis?source=bi&date=2025-01-25`
- XAI computes a live LIME explanation for that day's highest-demand reading
- Dates outside the data get a clear "No historical data" message
- All four components start with one command: `python start-all.py`

**Visual:** `viva/screenshots/07_bi_lime_button_row_2025-01-25.png` → arrow → `viva/screenshots/03_xai_lime_live_2025-01-25.png`.

**Speaker notes (50 s):** "Behaviour Intelligence detects abnormal days with Isolation Forest. Each row has a LIME button that opens my component for that exact date, and my backend computes the explanation live. Previously this link always showed the same sample from 2022; now it explains the clicked date, and says so clearly when there's no data. One limitation is shown on the page: the two components still use different dataset files, so the kW values differ."

---

## 12. Limitations, future work and conclusion

- **Limitations:** synthetic, exactly linear dataset; different file from BI; LIME unstable for medium demand; only XGBoost explained
- **Future:** retrain on BI's dataset (XGBoost R² 0.78 vs LR 0.30; SHAP spread over 4 features); lag features; explain the neural models; user study
- **Conclusion:** models, architecture and a full model + XAI comparison are now documented; SHAP was *proven* correct against ground truth, and LIME's weaknesses were quantified

**Visual:** none, or `viva/diagrams/evaluation_design.png` (small).

**Speaker notes (55 s):** "To be clear about limits: the dataset is synthetic and linear, which makes accuracy uninformative, though it let me validate the explainers. It also differs from BI's dataset. I analysed BI's data: there, XGBoost clearly beats linear regression and four features matter, so retraining on it is the next step, about a day of work. In summary, I addressed all three PP2 comments: the models, the architecture and a full comparison of both models and explanation methods. And I can now show that the explanations are correct. Thank you."
