# Model Training Outputs

## 1. profile_scaler.pkl
- **Purpose**: Standardizes 96-point daily demand profile features before clustering and anomaly detection.
- **Input**: p00 to p95 daily profile columns.
- **Output**: Scaled feature matrix.
- **Saved path**: models/profile_scaler.pkl
- **Why needed**: K-Means, DBSCAN, and Isolation Forest perform better when features are standardized.
- **Verification output**:
  - Feature count: 96
  - Number of daily profiles used: XXXX
  - File exists: Yes

## 2. kmeans_model.pkl
- **Purpose**: Groups similar daily demand profiles into recurring demand behavior clusters.
- **Input**: Scaled daily profile features.
- **Output**: kmeans_cluster for each day.
- **Saved path**: models/kmeans_model.pkl
- **Evaluation**:
  - Best K: X
  - Silhouette Score: X
  - Davies-Bouldin Index: X
  - Cluster distribution: {...}
- **File exists**: Yes

## 3. dbscan_model.pkl
- **Purpose**: Detects density-based profile groups and identifies noise/outlier demand days.
- **Input**: Scaled daily profile features.
- **Output**: dbscan_cluster and dbscan_noise_flag.
- **Saved path**: models/dbscan_model.pkl
- **Evaluation**:
  - Number of DBSCAN clusters: X
  - Noise point count: X
  - Noise percentage: X%
- **File exists**: Yes

## 4. isolation_forest_model.pkl
- **Purpose**: Detects abnormal daily demand profiles.
- **Input**: Scaled 96-point daily profile features.
- **Output**: isolation_anomaly_score and isolation_anomaly_flag.
- **Saved path**: models/isolation_forest_model.pkl
- **Evaluation**:
  - Total days analyzed: X
  - Anomaly days detected: X
  - Anomaly percentage: X%
- **File exists**: Yes

## Final Generated Outputs
List:
- data/processed/cleaned_data.csv
- data/processed/daily_profiles.csv
- data/processed/clustering_results.csv
- data/processed/anomaly_results.csv
- data/processed/peak_demand_results.csv
- data/processed/behavior_labels.csv
- models/clustering_metrics.json
- models/anomaly_metrics.json
- models/behavior_label_summary.json
