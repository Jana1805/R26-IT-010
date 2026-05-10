#!/usr/bin/env python3
"""
Complete ML Training Pipeline for Behavior Intelligence Module

This script runs the full training pipeline:
1. Load raw dataset
2. Preprocess data
3. Generate daily profiles
4. Train clustering models
5. Train anomaly detection
6. Detect peak demand days
7. Generate behavior labels
8. Save all models and processed data

Usage:
    python backend/app/ml/train_models.py
"""

import json
import sys
from pathlib import Path
from typing import Tuple

import pickle
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from scipy import stats

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import existing modules
from backend.app.ml.data_loader import load_raw_dataset
from backend.app.ml.preprocessing import preprocess_timeseries
from backend.app.ml.daily_profile import to_daily_profiles
from backend.app.ml.behavior_labeling import generate_behavior_labels_from_csv

# Constants
PROFILE_COLS = [f"p{str(i).zfill(2)}" for i in range(96)]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "load_forecasting_dataset_corrected.csv"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Create directories if they don't exist
for directory in [DATA_PROCESSED_DIR, MODELS_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def print_step_header(step: str, description: str):
    """Print a formatted step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {description}")
    print(f"{'='*60}")


def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"⚠️  {message}")


def step_1_load_raw_dataset() -> Tuple[pd.DataFrame, str, str]:
    """Load raw electricity demand dataset"""
    print("========================================")
    print("STEP 1: DATA LOADING")
    print("========================================")
    
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")
    
    try:
        df, ts_col, demand_col = load_raw_dataset(RAW_DATA_PATH)
        print("Raw dataset loaded successfully")
        print(f"Raw records: {len(df)}")
        print(f"Timestamp column: {ts_col}")
        print(f"Demand column: {demand_col}")
        
        # Remove duplicate timestamps
        original_len = len(df)
        df = df.drop_duplicates(subset=[ts_col], keep='first')
        if len(df) < original_len:
            print(f"Removed {original_len - len(df)} duplicate timestamps")
        
        return df, ts_col, demand_col
        
    except Exception as e:
        raise ValueError(f"Failed to load dataset: {str(e)}")


def step_2_preprocess_data(df: pd.DataFrame, ts_col: str, demand_col: str) -> pd.DataFrame:
    """Preprocess the raw data"""
    print("========================================")
    print("STEP 2: PREPROCESSING")
    print("========================================")
    
    try:
        df_clean = preprocess_timeseries(df, ts_col, demand_col)
        
        # Add additional time features
        df_clean['DayOfWeek'] = df_clean['Timestamp'].dt.dayofweek
        df_clean['Month'] = df_clean['Timestamp'].dt.month
        df_clean['IsWeekend'] = df_clean['DayOfWeek'].isin([5, 6]).astype(int)
        
        print("Missing values handled")
        print("Outliers removed")
        print(f"Cleaned records: {len(df_clean)}")
        
        # Save cleaned data
        cleaned_path = DATA_PROCESSED_DIR / "cleaned_data.csv"
        df_clean.to_csv(cleaned_path, index=False)
        print(f"Saved: data/processed/cleaned_data.csv")
        
        return df_clean
        
    except Exception as e:
        raise ValueError(f"Failed to preprocess data: {str(e)}")


def step_3_generate_daily_profiles(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Generate daily demand profiles with 96 points per day"""
    print("========================================")
    print("STEP 3: DAILY PROFILE GENERATION")
    print("========================================")
    
    try:
        daily_profiles = to_daily_profiles(df_clean)
        
        # Add additional daily statistics
        profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]
        
        # Calculate additional statistics
        daily_profiles['daily_min'] = daily_profiles[profile_cols].min(axis=1)
        daily_profiles['total_demand'] = daily_profiles[profile_cols].sum(axis=1)
        
        # Find peak time slot
        peak_slots = daily_profiles[profile_cols].idxmax(axis=1)
        daily_profiles['peak_time_slot'] = peak_slots.apply(lambda x: int(x[1:]) if isinstance(x, str) else x)
        
        # Add temporal features
        daily_profiles['date'] = pd.to_datetime(daily_profiles['date'])
        daily_profiles['day_of_week'] = daily_profiles['date'].dt.dayofweek
        daily_profiles['month'] = daily_profiles['date'].dt.month
        daily_profiles['is_weekend'] = (daily_profiles['day_of_week'].isin([5, 6])).astype(int)
        daily_profiles['date'] = daily_profiles['date'].dt.strftime('%Y-%m-%d')
        
        print("Daily profiles created")
        print(f"Total complete daily profiles: {len(daily_profiles)}")
        print("Profile columns: p00 to p95")
        
        # Save daily profiles
        profiles_path = DATA_PROCESSED_DIR / "daily_profiles.csv"
        daily_profiles.to_csv(profiles_path, index=False)
        print(f"Saved: data/processed/daily_profiles.csv")
        
        return daily_profiles
        
    except Exception as e:
        raise ValueError(f"Failed to generate daily profiles: {str(e)}")


def step_4_train_clustering_models(daily_profiles: pd.DataFrame) -> dict:
    """Train K-Means and DBSCAN clustering models"""
    print("========================================")
    print("STEP 4: PROFILE SCALER TRAINING")
    print("========================================")
    
    try:
        # Prepare features
        available_cols = [c for c in PROFILE_COLS if c in daily_profiles.columns]
        X = daily_profiles[available_cols].values
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        print("Model: StandardScaler")
        print("Input features: p00 to p95")
        print(f"Feature shape: ({len(daily_profiles)}, 96)")
        print("Scaler trained successfully")
        print("Saved model: models/profile_scaler.pkl")
        print(f"Scaler mean shape: {scaler.mean_.shape}")
        print(f"Scaler scale shape: {scaler.scale_.shape}")
        
        # Save scaler
        with open(MODELS_DIR / "profile_scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)
        
        print("========================================")
        print("STEP 5: K-MEANS TRAINING")
        print("========================================")
        
        # Find best K for K-Means
        print("Testing K values from 2 to 10...")
        best_k = 2
        best_score = -1
        k_scores = {}
        
        for k in range(2, 11):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=20)
            labels = kmeans.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            k_scores[k] = round(float(score), 4)
            
            if score > best_score:
                best_score = score
                best_k = k
        
        # Train final K-Means model
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=20)
        kmeans_labels = kmeans.fit_predict(X_scaled)
        
        # Calculate Davies-Bouldin Index
        dbi = davies_bouldin_score(X_scaled, kmeans_labels)
        
        print(f"Best K selected: {best_k}")
        print(f"Silhouette Score: {best_score:.4f}")
        print(f"Davies-Bouldin Index: {dbi:.4f}")
        print("K-Means model trained successfully")
        print("Saved model: models/kmeans_model.pkl")
        print("Saved results: data/processed/clustering_results.csv")
        
        # Save K-Means model
        with open(MODELS_DIR / "kmeans_model.pkl", "wb") as f:
            pickle.dump(kmeans, f)
        
        print("========================================")
        print("STEP 6: DBSCAN TRAINING")
        print("========================================")
        
        # Train DBSCAN
        eps = 1.6
        dbscan = None
        dbscan_labels = None
        
        for attempt in range(10):
            dbscan = DBSCAN(eps=eps, min_samples=8)
            dbscan_labels = dbscan.fit_predict(X_scaled)
            
            if not np.all(dbscan_labels == -1):
                break
            eps += 0.4
        
        noise_count = np.sum(dbscan_labels == -1)
        unique_clusters = len(np.unique(dbscan_labels[dbscan_labels != -1]))
        
        print("DBSCAN model trained successfully")
        print(f"Number of clusters: {unique_clusters}")
        print(f"Noise points: {noise_count}")
        print("Saved model: models/dbscan_model.pkl")
        print("DBSCAN labels added to clustering_results.csv")
        
        # Save DBSCAN model
        with open(MODELS_DIR / "dbscan_model.pkl", "wb") as f:
            pickle.dump(dbscan, f)
        
        # Prepare clustering results
        clustering_results = pd.DataFrame({
            'date': daily_profiles['date'],
            'kmeans_cluster': kmeans_labels,
            'dbscan_cluster': dbscan_labels,
            'dbscan_noise_flag': (dbscan_labels == -1).astype(int),
            'mean_demand': daily_profiles['mean_demand'],
            'peak_demand': daily_profiles['peak_demand'],
            'std_demand': daily_profiles['std_demand'],
            'day_of_week': daily_profiles['day_of_week'],
            'month': daily_profiles['month'],
            'is_weekend': daily_profiles['is_weekend']
        })
        
        # Calculate cluster distribution
        unique, counts = np.unique(kmeans_labels, return_counts=True)
        cluster_distribution = {int(k): int(v) for k, v in zip(unique, counts)}
        
        # Calculate DBSCAN cluster distribution (excluding noise)
        dbscan_unique, dbscan_counts = np.unique(dbscan_labels[dbscan_labels != -1], return_counts=True)
        dbscan_cluster_distribution = {int(k): int(v) for k, v in zip(dbscan_unique, dbscan_counts)}
        
        # Save clustering results
        clustering_results.to_csv(DATA_PROCESSED_DIR / "clustering_results.csv", index=False)
        
        # Save metrics
        clustering_metrics = {
            'best_k': int(best_k),
            'silhouette_score': round(float(best_score), 4),
            'davies_bouldin_index': round(float(dbi), 4),
            'cluster_distribution': cluster_distribution,
            'dbscan_noise_count': int(noise_count),
            'dbscan_cluster_distribution': dbscan_cluster_distribution,
            'k_silhouette_scores': k_scores
        }
        
        with open(MODELS_DIR / "clustering_metrics.json", 'w') as f:
            json.dump(clustering_metrics, f, indent=2)
        
        return clustering_metrics
        
    except Exception as e:
        raise ValueError(f"Failed to train clustering models: {str(e)}")


def step_5_train_anomaly_detection(daily_profiles: pd.DataFrame) -> dict:
    """Train Isolation Forest and calculate Z-Score for anomaly detection"""
    print("========================================")
    print("STEP 7: ISOLATION FOREST TRAINING")
    print("========================================")
    
    try:
        # Load scaler
        scaler_path = MODELS_DIR / "profile_scaler.pkl"
        if not scaler_path.exists():
            raise FileNotFoundError("Profile scaler not found. Run clustering step first.")
        
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        
        # Prepare features
        available_cols = [c for c in PROFILE_COLS if c in daily_profiles.columns]
        X = daily_profiles[available_cols].values
        X_scaled = scaler.transform(X)
        
        # Train Isolation Forest
        iso_forest = IsolationForest(
            n_estimators=300,
            contamination=0.03,
            random_state=42
        )
        iso_forest.fit(X_scaled)
        
        # Calculate anomaly scores
        iso_anomaly_scores = -iso_forest.decision_function(X_scaled)
        iso_anomaly_flags = iso_forest.predict(X_scaled) == -1
        
        print("Isolation Forest trained successfully")
        print(f"Anomaly days detected: {iso_anomaly_flags.sum()}")
        print(f"Anomaly percentage: {iso_anomaly_flags.mean()*100:.2f}%")
        print("Saved model: models/isolation_forest_model.pkl")
        print("Saved results: data/processed/anomaly_results.csv")
        
        # Calculate Z-Scores
        peak_z_scores = np.abs(stats.zscore(daily_profiles['peak_demand'], nan_policy='omit'))
        mean_z_scores = np.abs(stats.zscore(daily_profiles['mean_demand'], nan_policy='omit'))

        z_score_anomaly_flags = (peak_z_scores >= 3.0) | (mean_z_scores >= 3.0)

        # Combine anomaly flags
        final_anomaly_flags = iso_anomaly_flags | z_score_anomaly_flags

        # Create anomaly reasons
        anomaly_reasons = []
        for i in range(len(daily_profiles)):
            reasons = []
            if iso_anomaly_flags[i]:
                reasons.append(f"Isolation Forest (score: {iso_anomaly_scores[i]:.3f})")
            if z_score_anomaly_flags[i]:
                reasons.append(f"Z-Score (peak: {peak_z_scores[i]:.2f}, mean: {mean_z_scores[i]:.2f})")
            anomaly_reasons.append("; ".join(reasons) if reasons else "No anomaly")

        # Load clustering results to get kmeans_cluster, dbscan_cluster
        clustering_csv = pd.read_csv(DATA_PROCESSED_DIR / "clustering_results.csv")

        # Prepare anomaly results — column names match the API anomaly_detection.py output
        anomaly_results = pd.DataFrame({
            'date': daily_profiles['date'],
            'peak_demand': daily_profiles['peak_demand'],
            'mean_demand': daily_profiles['mean_demand'],
            'std_demand': daily_profiles['std_demand'],
            'isolation_anomaly_score': iso_anomaly_scores,
            'isolation_is_anomaly': iso_anomaly_flags,
            'peak_zscore': peak_z_scores,
            'mean_zscore': mean_z_scores,
            'zscore_is_anomaly': z_score_anomaly_flags,
            'final_is_anomaly': final_anomaly_flags,
            'anomaly_reason': anomaly_reasons
        })

        anomaly_results = anomaly_results.merge(
            clustering_csv[['date', 'kmeans_cluster', 'dbscan_cluster']], on='date', how='left'
        )

        # Save model and results
        with open(MODELS_DIR / "isolation_forest_model.pkl", "wb") as f:
            pickle.dump(iso_forest, f)
        anomaly_results.to_csv(DATA_PROCESSED_DIR / "anomaly_results.csv", index=False)
        
        # Calculate and save metrics
        total_days = len(daily_profiles)
        anomaly_metrics = {
            'total_days': total_days,
            'anomaly_days': int(final_anomaly_flags.sum()),
            'anomaly_percentage': round(float(final_anomaly_flags.mean()) * 100, 2),
            'isolation_forest_anomaly_count': int(iso_anomaly_flags.sum()),
            'z_score_anomaly_count': int(z_score_anomaly_flags.sum()),
            'final_anomaly_count': int(final_anomaly_flags.sum()),
            'note': "Precision, Recall, and F1-score require verified abnormal event labels and are not calculated in this version."
        }
        
        with open(MODELS_DIR / "anomaly_metrics.json", 'w') as f:
            json.dump(anomaly_metrics, f, indent=2)
        
        return anomaly_metrics
        
    except Exception as e:
        raise ValueError(f"Failed to train anomaly detection models: {str(e)}")


def step_6_detect_peak_demand_days(daily_profiles: pd.DataFrame) -> dict:
    """Detect peak demand days using percentile thresholds"""
    print("========================================")
    print("STEP 8: PEAK DEMAND DETECTION")
    print("========================================")
    
    try:
        # Load anomaly results
        anomaly_path = DATA_PROCESSED_DIR / "anomaly_results.csv"
        if not anomaly_path.exists():
            raise FileNotFoundError("Anomaly results not found. Run anomaly detection step first.")
        
        anomaly_results = pd.read_csv(anomaly_path)

        # Calculate thresholds
        peak_threshold_90 = daily_profiles['peak_demand'].quantile(0.90)
        peak_threshold_75 = daily_profiles['peak_demand'].quantile(0.75)

        print(f"Peak threshold: {peak_threshold_90:.2f}")

        # Apply peak detection logic
        cond_90 = daily_profiles['peak_demand'] >= peak_threshold_90
        cond_anomaly = anomaly_results['final_is_anomaly'] & (daily_profiles['peak_demand'] >= peak_threshold_75)

        is_peak_demand_day = cond_90 | cond_anomaly

        # Generate peak reasons — column names match API peak_detection.py output
        peak_reasons = []
        for i in range(len(daily_profiles)):
            reasons = []
            if cond_90.iloc[i]:
                reasons.append(f"peak_demand >= 90th percentile ({peak_threshold_90:.1f} kW)")
            if cond_anomaly.iloc[i]:
                reasons.append(f"anomaly with peak_demand >= 75th percentile ({peak_threshold_75:.1f} kW)")
            peak_reasons.append("; ".join(reasons) if reasons else "not a peak day")

        # Build peak_demand_results merging anomaly columns so behavior_labeling.py can read them
        peak_results = daily_profiles[['date', 'peak_demand', 'mean_demand']].copy()
        peak_results['threshold_90th_percentile'] = peak_threshold_90
        peak_results['threshold_75th_percentile'] = peak_threshold_75
        peak_results['is_peak_demand_day'] = is_peak_demand_day.values
        peak_results['peak_reason'] = peak_reasons

        merge_cols = ['date', 'final_is_anomaly', 'isolation_anomaly_score',
                      'peak_zscore', 'mean_zscore', 'zscore_is_anomaly',
                      'isolation_is_anomaly', 'kmeans_cluster', 'dbscan_cluster']
        available_merge = [c for c in merge_cols if c in anomaly_results.columns]
        peak_results = peak_results.merge(
            anomaly_results[available_merge], on='date', how='left'
        )

        # Save results
        peak_results.to_csv(DATA_PROCESSED_DIR / "peak_demand_results.csv", index=False)
        
        # Calculate metrics
        peak_metrics = {
            'total_days': len(daily_profiles),
            'peak_days': int(is_peak_demand_day.sum()),
            'non_peak_days': int((~is_peak_demand_day).sum()),
            'peak_threshold_90th_percentile': round(float(peak_threshold_90), 2),
            'peak_threshold_75th_percentile': round(float(peak_threshold_75), 2)
        }
        
        print(f"Peak demand days: {is_peak_demand_day.sum()}")
        print("Saved: data/processed/peak_demand_results.csv")
        
        return peak_metrics
        
    except Exception as e:
        raise ValueError(f"Failed to detect peak demand days: {str(e)}")


def step_7_generate_behavior_labels() -> dict:
    """Generate behavior labels based on all previous results"""
    print("========================================")
    print("STEP 9: BEHAVIOR LABEL GENERATION")
    print("========================================")
    
    try:
        # Delegate to the same function the API uses — guarantees identical output format
        result = generate_behavior_labels_from_csv(
            peak_demand_results_path=DATA_PROCESSED_DIR / "peak_demand_results.csv",
            output_path=DATA_PROCESSED_DIR / "behavior_labels.csv",
        )

        low_threshold = result['low_demand_threshold']
        print_info(f"Low demand threshold (25th percentile): {low_threshold:.2f} kW")
        print_success("Behavior labels generated!")
        for label, count in result['label_counts'].items():
            pct = result['label_percentages'][label]
            print_info(f"{label}: {count} days ({pct}%)")

        # Save summary JSON
        behavior_summary = {
            'total_days': result['total_days'],
            'label_counts': result['label_counts'],
            'label_percentages': result['label_percentages'],
            'low_demand_threshold': low_threshold,
            'risk_distribution': result.get('risk_distribution', {}),
        }
        with open(MODELS_DIR / "behavior_label_summary.json", 'w') as f:
            json.dump(behavior_summary, f, indent=2)

        return behavior_summary

    except Exception as e:
        raise ValueError(f"Failed to generate behavior labels: {str(e)}")


def step_8_final_validation():
    """Print final training summary"""
    print("========================================")
    print("FINAL MODEL FILE VERIFICATION")
    print("========================================")
    
    # Check if all model files exist
    model_files = [
        "models/profile_scaler.pkl",
        "models/kmeans_model.pkl", 
        "models/dbscan_model.pkl",
        "models/isolation_forest_model.pkl"
    ]
    
    for model_file in model_files:
        model_path = PROJECT_ROOT / model_file
        status = "FOUND" if model_path.exists() else "NOT FOUND"
        print(f"{model_file}: {status}")
    
    print("\nTraining pipeline completed successfully.")
    
    try:
        # Load all metrics
        clustering_metrics = json.load(open(MODELS_DIR / "clustering_metrics.json"))
        anomaly_metrics = json.load(open(MODELS_DIR / "anomaly_metrics.json"))
        behavior_summary = json.load(open(MODELS_DIR / "behavior_label_summary.json"))
        
        # Load data info
        cleaned_data = pd.read_csv(DATA_PROCESSED_DIR / "cleaned_data.csv")
        daily_profiles = pd.read_csv(DATA_PROCESSED_DIR / "daily_profiles.csv")
        
        print_success("🎉 TRAINING PIPELINE COMPLETED SUCCESSFULLY! 🎉")
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        
        print(f"\n📊 DATA PROCESSING:")
        print(f"   Raw records: {len(cleaned_data):,}")
        print(f"   Daily profiles: {len(daily_profiles)}")
        print(f"   Date range: {cleaned_data['Timestamp'].min()} to {cleaned_data['Timestamp'].max()}")
        
        print(f"\n🤖 CLUSTERING RESULTS:")
        print(f"   Best K for K-Means: {clustering_metrics['best_k']}")
        print(f"   Silhouette Score: {clustering_metrics['silhouette_score']:.4f}")
        print(f"   Davies-Bouldin Index: {clustering_metrics['davies_bouldin_index']:.4f}")
        print(f"   DBSCAN noise points: {clustering_metrics['dbscan_noise_count']}")
        
        print(f"\n🚨 ANOMALY DETECTION:")
        print(f"   Anomaly days: {anomaly_metrics['anomaly_days']} ({anomaly_metrics['anomaly_percentage']:.2f}%)")
        print(f"   Isolation Forest anomalies: {anomaly_metrics['isolation_forest_anomaly_count']}")
        print(f"   Z-Score anomalies: {anomaly_metrics['z_score_anomaly_count']}")
        
        print(f"\n🏷️  BEHAVIOR LABELS:")
        for label, count in behavior_summary['label_counts'].items():
            percentage = behavior_summary['label_percentages'][label]
            print(f"   {label}: {count} days ({percentage}%)")
        
        print(f"\n💾 FILES GENERATED:")
        print(f"\n📁 Processed Data (data/processed/):")
        for file in ["cleaned_data.csv", "daily_profiles.csv", "clustering_results.csv", 
                    "anomaly_results.csv", "peak_demand_results.csv", "behavior_labels.csv"]:
            path = DATA_PROCESSED_DIR / file
            if path.exists():
                size = path.stat().st_size / 1024 / 1024  # MB
                print(f"   ✅ {file} ({size:.1f} MB)")
        
        print(f"\n🤖 Trained Models (models/):")
        for file in ["profile_scaler.pkl", "kmeans_model.pkl", "dbscan_model.pkl", 
                    "isolation_forest_model.pkl"]:
            path = MODELS_DIR / file
            if path.exists():
                size = path.stat().st_size / 1024 / 1024  # MB
                print(f"   ✅ {file} ({size:.1f} MB)")
        
        print(f"\n📈 Metrics (models/):")
        for file in ["clustering_metrics.json", "anomaly_metrics.json", "behavior_label_summary.json"]:
            path = MODELS_DIR / file
            if path.exists():
                print(f"   ✅ {file}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Start the backend API: uvicorn backend.app.main:app --reload --port 8001")
        print(f"   2. Start the frontend: cd frontend && npm start")
        print(f"   3. Access the dashboard at: http://localhost:3000")
        
        print("\n" + "="*60)
        print("✨ READY FOR BEHAVIOR INTELLIGENCE ANALYSIS! ✨")
        print("="*60)
        
    except Exception as e:
        print_warning(f"Could not load final metrics: {str(e)}")


def main():
    """Main training pipeline function"""
    print("🚀 STARTING BEHAVIOR INTELLIGENCE TRAINING PIPELINE 🚀")
    print(f"Project root: {PROJECT_ROOT}")
    
    try:
        # Step 1: Load raw dataset
        df_raw, ts_col, demand_col = step_1_load_raw_dataset()
        
        # Step 2: Preprocess data
        df_clean = step_2_preprocess_data(df_raw, ts_col, demand_col)
        
        # Step 3: Generate daily profiles
        daily_profiles = step_3_generate_daily_profiles(df_clean)
        
        # Step 4: Train clustering models
        clustering_metrics = step_4_train_clustering_models(daily_profiles)
        
        # Step 5: Train anomaly detection
        anomaly_metrics = step_5_train_anomaly_detection(daily_profiles)
        
        # Step 6: Detect peak demand days
        peak_metrics = step_6_detect_peak_demand_days(daily_profiles)
        
        # Step 7: Generate behavior labels
        behavior_summary = step_7_generate_behavior_labels()
        
        # Step 8: Final validation
        step_8_final_validation()
        
        print("\n🎉 Training pipeline completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Training pipeline failed. Please check the error message above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
