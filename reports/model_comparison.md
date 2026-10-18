# Model Comparison Report — Behaviour Intelligence

## 1. Clustering Model Comparison

| Model                |   K |   Silhouette |   DaviesBouldin |   CalinskiHarabasz |
|:---------------------|----:|-------------:|----------------:|-------------------:|
| Agglomerative (Ward) |   2 |       0.0044 |         16.7498 |             6.6575 |
| Gaussian Mixture     |   7 |       0.0091 |          6.6832 |            13.3904 |
| K-Means              |   2 |       0.011  |          9.2448 |            22.9548 |

**Baseline (PP1, raw 96-dim K-Means):** Silhouette 0.0097, Davies-Bouldin 9.78


## 2. Anomaly Detection Model Comparison

| Model              |   Flagged |   Percent |
|:-------------------|----------:|----------:|
| IsolationForest    |        60 |      3.03 |
| LocalOutlierFactor |        60 |      3.03 |
| OneClassSVM        |        93 |      4.7  |

## 3. Data Integrity Diagnostics

- Mean adjacent 15-min slot correlation: **0.003** (real load data: >0.85)
- PCA components for 90% variance: **82 / 96**
- Solar irradiance at midnight: **250 W/m²** (physically impossible)
- Temperature: **28.0 °C at every hour**
- Correlation(Load Demand, Temperature) = **1.000000** — temperature is a linear transform of load

**Conclusion:** the supplied dataset is synthetic and contains no temporal or cross-variable structure.
