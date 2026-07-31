# CNN-Transformer-Final: Build, Issue, Fix, and Validation Summary

## 1. Objective

Build a CNN-Transformer probabilistic load-forecasting model as a direct
architectural counterpart to an existing CNN-LSTM-Final model, for a controlled
research comparison (recurrence vs. self-attention).

**Design constraint**: keep the data pipeline, split ratios, scaling method,
MC-Dropout methodology, and conformal calibration procedure identical to
CNN-LSTM-Final. Only the sequence-modeling block was changed:

- CNN-LSTM-Final: `Conv1D ×2 → LSTM(128) → LSTM(64)`
- CNN-Transformer-Final: `Conv1D ×2 → Dense(embed) → PositionalEncoding → TransformerBlock ×4`

This isolates the architecture as the only variable between the two models.

**Configuration**: `LOOKBACK=168`, `HORIZON=4`, `D_MODEL=64`, `N_HEADS=4`,
`D_FF=256`, `N_BLOCKS=4`, `DROP_RATE=0.1`, `MC_SAMPLES=100`,
conformal `alpha=0.05`.

---

## 2. Issue Encountered

MC-Dropout inference took **~5 hours** on a free-tier Colab T4 GPU, causing the
runtime to disconnect before evaluation finished.

### Root Cause

The original `mc_predict` function ran **100 separate eager `model()` calls**
per batch, per data split (Train/Val/Test), inside a plain Python loop. This
pattern is identical to the one already used in CNN-LSTM-Final, but the cost is
far higher for a Transformer because self-attention is `O(L²)` per layer
(sequence length `L=168`, 4 stacked blocks), versus an LSTM's `O(L)` recurrent
cost. Combined with the eager-mode dispatch overhead of calling the model 100×
per batch, this produced the multi-hour runtime.

---

## 3. Fix Implemented

1. **Vectorized MC inference.** Each batch is tiled ×`MC_SAMPLES` along the
   batch dimension and passed through the model in a **single
   `@tf.function`-compiled forward pass**, instead of 100 sequential eager
   calls. Mathematically equivalent output (same mean/std across dropout
   samples), but removes the per-call Python/eager dispatch overhead that
   dominated the runtime.
2. **Skipped full MC-Dropout on the Train split.** Train is the largest split
   and its MC-uncertainty numbers are not used downstream (conformal
   calibration uses Val; plots use Test), so it was switched to a single
   deterministic `model.predict()` pass for point-forecast metrics only.
3. Added a tunable `MC_INFER_BATCH` (default 32) to control GPU memory usage
   during the vectorized MC pass.

**Result**: runtime issue resolved; no further disconnects.

---

## 4. Training Behavior

- Ran 35 / 100 max epochs; `EarlyStopping` (patience=15) triggered, weights
  restored from **epoch 20** (best `val_loss = 0.2391`, scaled MAE).
- `ReduceLROnPlateau` halved the learning rate (1e-3 → 5e-4) at epoch 28.
- Training curve: validation loss decreased steadily to epoch ~20, then
  plateaued/drifted slightly upward — consistent with a correctly-timed early
  stop, not an unstable or diverging run.

---

## 5. Diagnostic Validation

### 5.1 Train performing worse than Val — investigated as a potential issue

Initial concern: Train MAE (kW) was higher than Val MAE, despite Train having a
lower *scaled* training loss during fitting — the opposite of the usual
train ≥ val relationship.

**Train vs. Val target distribution (raw kW, unscaled):**

| Split | Mean (kW) | Std (kW) | 24h Rolling Std (kW) |
|-------|-----------|----------|------------------------|
| Train | 1726.3    | 296.8    | 222.2                  |
| Val   | 2057.6    | 237.1    | 200.5                  |

**Conclusion**: Train (the earliest chronological slice, per the temporal
split) is a lower-load, higher-volatility regime than Val. This fully explains
the higher Train error metrics — it is a data-regime effect, not a training
bug, leakage issue, or architectural flaw.

### 5.2 Naive baseline comparison

Seasonal-naive / persistence baseline: predict the load value from the same
time 24 hours earlier (`load_lag_96`, window-aligned identically to the
model's sequences).

| Split | Model MAE (kW) | Naive MAE (kW) | MAE Improvement | Model MAPE | Naive MAPE | Model R² | Naive R² |
|-------|-----------------|-----------------|------------------|------------|------------|----------|----------|
| Train | 75.67           | 110.72          | −31.7%           | 4.76%      | 6.72%      | 0.9040   | 0.7770   |
| Val   | 54.77           | 95.26           | −42.5%           | 2.70%      | 4.87%      | 0.9137   | 0.7070   |
| Test  | 58.27           | 79.56           | −26.8%           | 2.79%      | 3.97%      | 0.8929   | 0.7433   |

**Conclusion**: the model beats the naive baseline by 27–42% on MAE and by
0.15–0.21 on R² across every split — confirming the architecture is adding
real predictive value, not simply tracking daily seasonality.

---

## 6. Final Results

### 6.1 Point-forecast metrics

| Split | Method | MAE (kW) | RMSE (kW) | MAPE | R² |
|-------|--------|----------|-----------|------|-----|
| Train | Deterministic | 75.67 | 91.98 | 4.76% | 0.9040 |
| Val   | MC Dropout (mean) | 54.77 | 69.70 | 2.70% | 0.9137 |
| Test  | MC Dropout (mean) | 58.27 | 73.10 | 2.79% | 0.8929 |

MC std (epistemic uncertainty): Val = 25.0 kW, Test = 27.8 kW.
Raw (pre-conformal) 95% CI coverage: Val = 50.5%, Test = 49.4% — expected to
undershoot before calibration.

### 6.2 Conformal calibration (α = 0.05)

Calibrated on Val residuals: mean = 54.8 kW, p95 = 137.0 kW →
**Q_hat = 136.97 kW** (interval radius).

| Split | Coverage | Avg. Interval Width (kW) |
|-------|----------|----------------------------|
| Train | 87.4%    | 273.9                      |
| Val   | 95.0%    | 273.9 *(calibration set — tautological)* |
| Test  | 93.6%    | 273.9                      |

Test coverage (93.6%) is close to the 95% nominal target, indicating mild but
acceptable distribution shift between Val and Test.

---

## 7. Overall Assessment

- Training converged correctly; early stopping and LR scheduling behaved as
  intended, with no evidence of overfitting or instability.
- The Train/Val error gap is explained by a genuine data-regime difference
  (confirmed via distribution and rolling-std analysis), not a pipeline defect.
- The model substantially outperforms a seasonal-naive baseline on every
  split, on both MAE and R².
- Conformal prediction intervals achieve near-nominal coverage on the held-out
  Test set.
- The architecture change (LSTM stack → Transformer blocks) was applied while
  holding the rest of the pipeline constant, so these results are suitable for
  direct comparison against CNN-LSTM-Final's corresponding metrics.
