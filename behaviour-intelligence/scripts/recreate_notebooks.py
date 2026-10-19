#!/usr/bin/env python3
"""
Recreate all Jupyter notebooks using nbformat to fix corrupted JSON issues.

This script recreates all 5 notebooks with proper JSON structure:
- 01_data_preprocessing.ipynb
- 02_daily_profile_generation.ipynb  
- 03_clustering_model_training.ipynb
- 04_anomaly_detection_training.ipynb
- 05_behavior_label_generation.ipynb

Usage:
    python scripts/recreate_notebooks.py
"""

import sys
from pathlib import Path
import nbformat as nbf

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def create_notebook_01():
    """Create 01_data_preprocessing.ipynb"""
    nb = nbf.v4.new_notebook()
    
    # Title cell
    nb.cells.append(nbf.v4.new_markdown_cell("# Data Preprocessing"))
    nb.cells.append(nbf.v4.new_markdown_cell("""
This notebook loads raw 15-minute electricity demand data and creates cleaned_data.csv.

## Steps:
1. Load raw dataset from data/raw/load_forecasting_dataset_corrected.csv
2. Detect timestamp and demand columns automatically
3. Convert timestamp to datetime and sort
4. Remove duplicate timestamps
5. Resample to 15-minute intervals
6. Handle missing values using interpolation
7. Remove impossible negative demand values
8. Remove extreme outliers using IQR
9. Add time features (Date, Hour, Minute, DayOfWeek, Month, IsWeekend)
10. Save cleaned data to data/processed/cleaned_data.csv
"""))
    
    # Import cell
    nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path().resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up paths
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DATA_PATH = DATA_RAW_DIR / "load_forecasting_dataset_corrected.csv"
CLEANED_DATA_PATH = DATA_PROCESSED_DIR / "cleaned_data.csv"

print(f"Project root: {PROJECT_ROOT}")
print(f"Raw data path: {RAW_DATA_PATH}")
print(f"Processed data path: {DATA_PROCESSED_DIR}")
"""))
    
    # Load data cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Load raw dataset
if not RAW_DATA_PATH.exists():
    raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}")

print(f"Loading raw dataset from: {RAW_DATA_PATH}")
df_raw = pd.read_csv(RAW_DATA_PATH)

print(f"Raw dataset loaded successfully!")
print(f"Shape: {df_raw.shape}")
print(f"Columns: {list(df_raw.columns)}")
print(f"First few rows:")
print(df_raw.head())
"""))
    
    # Detect columns cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Detect timestamp column automatically
timestamp_cols = [col for col in df_raw.columns if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp'])]
if timestamp_cols:
    ts_col = timestamp_cols[0]
else:
    # Try to find datetime-like columns
    for col in df_raw.columns:
        try:
            pd.to_datetime(df_raw[col].head(100))
            ts_col = col
            break
        except:
            continue

# Detect demand column automatically  
demand_keywords = ['demand', 'load', 'consumption', 'power', 'energy', 'kw']
demand_cols = [col for col in df_raw.columns if any(keyword in col.lower() for keyword in demand_keywords)]
if demand_cols:
    demand_col = demand_cols[0]
else:
    # Use first numeric column that's not timestamp
    for col in df_raw.columns:
        if col != ts_col and df_raw[col].dtype in ['int64', 'float64']:
            demand_col = col
            break

print(f"Detected timestamp column: {ts_col}")
print(f"Detected demand column: {demand_col}")
"""))
    
    # Preprocessing cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Convert timestamp to datetime
df_raw[ts_col] = pd.to_datetime(df_raw[ts_col], errors='coerce')

# Sort by timestamp
df_raw = df_raw.sort_values(ts_col)

# Remove duplicate timestamps
original_len = len(df_raw)
df_raw = df_raw.drop_duplicates(subset=[ts_col], keep='first')
duplicates_removed = original_len - len(df_raw)
print(f"Removed {duplicates_removed} duplicate timestamps")

# Handle missing timestamps
df_raw = df_raw.dropna(subset=[ts_col])

print(f"Data after cleaning: {len(df_raw)} records")
print(f"Date range: {df_raw[ts_col].min()} to {df_raw[ts_col].max()}")
"""))
    
    # Resampling cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Set timestamp as index for resampling
df_indexed = df_raw.set_index(ts_col)

# Resample to 15-minute intervals
df_resampled = df_indexed.resample('15T').mean()

# Remove rows with missing demand values
df_resampled = df_resampled.dropna(subset=[demand_col])

print(f"After resampling to 15-minute intervals: {len(df_resampled)} records")
print(f"Date range: {df_resampled.index.min()} to {df_resampled.index.max()}")
"""))
    
    # Handle missing values and outliers cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Remove impossible negative demand values
negative_count = (df_resampled[demand_col] < 0).sum()
df_clean = df_resampled[df_resampled[demand_col] >= 0]
print(f"Removed {negative_count} negative demand values")

# Remove extreme outliers using IQR method
Q1 = df_clean[demand_col].quantile(0.25)
Q3 = df_clean[demand_col].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outliers = (df_clean[demand_col] < lower_bound) | (df_clean[demand_col] > upper_bound)
outlier_count = outliers.sum()
df_clean = df_clean[~outliers]

print(f"Removed {outlier_count} outliers using IQR method")
print(f"Final cleaned data: {len(df_clean)} records")
"""))
    
    # Add time features cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Reset index to get timestamp back as column
df_clean = df_clean.reset_index()

# Add time features
df_clean['Date'] = df_clean[ts_col].dt.date
df_clean['Hour'] = df_clean[ts_col].dt.hour
df_clean['Minute'] = df_clean[ts_col].dt.minute
df_clean['DayOfWeek'] = df_clean[ts_col].dt.dayofweek
df_clean['Month'] = df_clean[ts_col].dt.month
df_clean['IsWeekend'] = (df_clean['DayOfWeek'].isin([5, 6])).astype(int)

# Reorder columns
cols = [ts_col, demand_col, 'Date', 'Hour', 'Minute', 'DayOfWeek', 'Month', 'IsWeekend']
df_clean = df_clean[cols]

print("Added time features:")
print(f"- Date: {df_clean['Date'].min()} to {df_clean['Date'].max()}")
print(f"- Hours: {df_clean['Hour'].min()} to {df_clean['Hour'].max()}")
print(f"- DayOfWeek: {sorted(df_clean['DayOfWeek'].unique())}")
print(f"- Month: {sorted(df_clean['Month'].unique())}")
print(f"- Weekend days: {df_clean['IsWeekend'].sum()}")
"""))
    
    # Save data cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Create processed directory
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Save cleaned data
df_clean.to_csv(CLEANED_DATA_PATH, index=False)

print(f"Cleaned data saved to: {CLEANED_DATA_PATH}")
print(f"Final shape: {df_clean.shape}")
print(f"File size: {CLEANED_DATA_PATH.stat().st_size / 1024 / 1024:.1f} MB")

print("\\nFinal data summary:")
print(df_clean[[demand_col, 'Hour', 'DayOfWeek', 'Month']].describe())
"""))
    
    return nb

def create_notebook_02():
    """Create 02_daily_profile_generation.ipynb"""
    nb = nbf.v4.new_notebook()
    
    # Title cell
    nb.cells.append(nbf.v4.new_markdown_cell("# Daily Profile Generation"))
    nb.cells.append(nbf.v4.new_markdown_cell("""
This notebook converts 15-minute electricity demand data into daily profiles with 96 quarter-hour demand points.

## Steps:
1. Load cleaned data from data/processed/cleaned_data.csv
2. Create time_slot from Hour and Minute (0-95)
3. Pivot each Date into p00 to p95 columns
4. Remove incomplete days
5. Calculate daily statistics (mean, peak, min, std, etc.)
6. Add temporal features
7. Save daily profiles to data/processed/daily_profiles.csv
"""))
    
    # Import cell
    nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path().resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up paths
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEANED_DATA_PATH = DATA_PROCESSED_DIR / "cleaned_data.csv"
DAILY_PROFILES_PATH = DATA_PROCESSED_DIR / "daily_profiles.csv"

print(f"Project root: {PROJECT_ROOT}")
print(f"Cleaned data path: {CLEANED_DATA_PATH}")
print(f"Daily profiles path: {DAILY_PROFILES_PATH}")
"""))
    
    # Load cleaned data cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Load cleaned data
if not CLEANED_DATA_PATH.exists():
    raise FileNotFoundError(f"Cleaned data not found at {CLEANED_DATA_PATH}")

df_clean = pd.read_csv(CLEANED_DATA_PATH)

print(f"Cleaned data loaded successfully!")
print(f"Shape: {df_clean.shape}")
print(f"Date range: {df_clean['Date'].min()} to {df_clean['Date'].max()}")
print(f"Columns: {list(df_clean.columns)}")
print(f"\\nFirst few rows:")
print(df_clean.head())
"""))
    
    # Create time slots cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Create time_slot from Hour and Minute (0-95 for 15-minute intervals)
df_clean['time_slot'] = df_clean['Hour'] * 4 + df_clean['Minute'] // 15

print(f"Time slots created: {df_clean['time_slot'].min()} to {df_clean['time_slot'].max()}")
print(f"Unique time slots: {sorted(df_clean['time_slot'].unique())}")
"""))
    
    # Pivot to create profiles cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Get demand column name (assuming it's the second column after timestamp)
demand_col = df_clean.columns[1]  # Usually the demand/load column
timestamp_col = df_clean.columns[0]  # Usually the timestamp column

print(f"Using demand column: {demand_col}")
print(f"Using timestamp column: {timestamp_col}")

# Pivot to create daily profiles
daily_profiles = df_clean.pivot_table(
    index='Date',
    columns='time_slot',
    values=demand_col,
    aggfunc='mean'
)

# Rename columns to p00, p01, ..., p95
daily_profiles.columns = [f"p{str(col).zfill(2)}" for col in daily_profiles.columns]

print(f"Daily profiles created: {daily_profiles.shape}")
print(f"Profile columns: {list(daily_profiles.columns)}")
print(f"\\nFirst few rows:")
print(daily_profiles.head())
"""))
    
    # Remove incomplete days cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Remove days with missing time slots (incomplete days)
complete_days = daily_profiles.notna().all(axis=1)
daily_profiles = daily_profiles[complete_days]

print(f"Complete days: {complete_days.sum()}/{len(daily_profiles)}")
print(f"Removed {len(daily_profiles) - complete_days.sum()} incomplete days")
print(f"Final daily profiles: {daily_profiles.shape}")

# Fill any remaining missing values with interpolation
daily_profiles = daily_profiles.interpolate(method='linear', axis=1)
daily_profiles = daily_profiles.fillna(method='bfill', axis=1).fillna(method='ffill', axis=1)
"""))
    
    # Calculate daily statistics cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Calculate daily statistics
profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]

daily_profiles['daily_mean'] = daily_profiles[profile_cols].mean(axis=1)
daily_profiles['daily_peak'] = daily_profiles[profile_cols].max(axis=1)
daily_profiles['daily_min'] = daily_profiles[profile_cols].min(axis=1)
daily_profiles['daily_std'] = daily_profiles[profile_cols].std(axis=1)
daily_profiles['total_demand'] = daily_profiles[profile_cols].sum(axis=1)

# Find peak time slot
daily_profiles['peak_time_slot'] = daily_profiles[profile_cols].idxmax(axis=1)
daily_profiles['peak_time_slot'] = daily_profiles['peak_time_slot'].str.replace('p', '').astype(int)

print("Daily statistics calculated:")
print(f"- Mean demand: {daily_profiles['daily_mean'].mean():.2f} kW")
print(f"- Peak demand: {daily_profiles['daily_peak'].mean():.2f} kW")
print(f"- Std demand: {daily_profiles['daily_std'].mean():.2f} kW")
"""))
    
    # Add temporal features cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Convert Date to datetime and add temporal features
daily_profiles.index = pd.to_datetime(daily_profiles.index)
daily_profiles['date'] = daily_profiles.index.strftime('%Y-%m-%d')
daily_profiles['day_of_week'] = daily_profiles.index.dayofweek
daily_profiles['month'] = daily_profiles.index.month
daily_profiles['is_weekend'] = (daily_profiles.index.dayofweek.isin([5, 6])).astype(int)

# Reorder columns to have date first, then stats, then profiles
base_cols = ['date', 'daily_mean', 'daily_peak', 'daily_min', 'daily_std', 
            'total_demand', 'peak_time_slot', 'day_of_week', 'month', 'is_weekend']
profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]
all_cols = base_cols + profile_cols
daily_profiles = daily_profiles[all_cols]

print("Temporal features added:")
print(f"- Date range: {daily_profiles['date'].min()} to {daily_profiles['date'].max()}")
print(f"- Days of week: {sorted(daily_profiles['day_of_week'].unique())}")
print(f"- Months: {sorted(daily_profiles['month'].unique())}")
print(f"- Weekend days: {daily_profiles['is_weekend'].sum()}")
"""))
    
    # Save daily profiles cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Save daily profiles
daily_profiles.to_csv(DAILY_PROFILES_PATH, index=False)

print(f"Daily profiles saved to: {DAILY_PROFILES_PATH}")
print(f"Final shape: {daily_profiles.shape}")
print(f"File size: {DAILY_PROFILES_PATH.stat().st_size / 1024 / 1024:.1f} MB")

print("\\nDaily profiles summary:")
print(f"- Total profiles: {len(daily_profiles)}")
print(f"- Profile columns: {len([col for col in daily_profiles.columns if col.startswith('p')])}")
print(f"- Date range: {daily_profiles['date'].min()} to {daily_profiles['date'].max()}")

print("\\nSample of final data:")
print(daily_profiles[['date', 'daily_mean', 'daily_peak', 'daily_peak']].head())
"""))
    
    return nb

def create_notebook_03():
    """Create 03_clustering_model_training.ipynb"""
    nb = nbf.v4.new_notebook()
    
    # Title cell
    nb.cells.append(nbf.v4.new_markdown_cell("# Clustering Model Training"))
    nb.cells.append(nbf.v4.new_markdown_cell("""
This notebook trains clustering models to identify demand patterns in daily electricity consumption profiles.

## Models Used:
- **StandardScaler**: Standardizes 96-point daily profile features
- **K-Means**: Groups similar daily demand profiles into clusters
- **DBSCAN**: Density-based clustering for pattern detection
- **Silhouette Score**: Evaluates clustering quality
- **Davies-Bouldin Index**: Another clustering quality metric

## Steps:
1. Load daily profiles from data/processed/daily_profiles.csv
2. Select p00 to p95 features for clustering
3. Train StandardScaler and save to models/profile_scaler.pkl
4. Test K-Means with K=2 to 10 and select best K
5. Train final K-Means and save to models/kmeans_model.pkl
6. Train DBSCAN and save to models/dbscan_model.pkl
7. Create clustering results and save metrics
"""))
    
    # Import cell
    nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path().resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import sklearn components
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score

# Set up paths
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DAILY_PROFILES_PATH = DATA_PROCESSED_DIR / "daily_profiles.csv"
CLUSTERING_RESULTS_PATH = DATA_PROCESSED_DIR / "clustering_results.csv"

# Create models directory
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Project root: {PROJECT_ROOT}")
print(f"Daily profiles path: {DAILY_PROFILES_PATH}")
print(f"Models directory: {MODELS_DIR}")
"""))
    
    # Load daily profiles cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Load daily profiles
if not DAILY_PROFILES_PATH.exists():
    raise FileNotFoundError(f"Daily profiles not found at {DAILY_PROFILES_PATH}")

daily_profiles = pd.read_csv(DAILY_PROFILES_PATH)

print(f"Daily profiles loaded successfully!")
print(f"Shape: {daily_profiles.shape}")
print(f"Date range: {daily_profiles['date'].min()} to {daily_profiles['date'].max()}")

# Get profile columns
profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]
available_cols = [col for col in profile_cols if col in daily_profiles.columns]

print(f"Profile columns available: {len(available_cols)}")
print(f"\\nFirst few rows:")
print(daily_profiles[['date', 'daily_mean', 'daily_peak']].head())
"""))
    
    # Prepare features cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Prepare features for clustering
X = daily_profiles[available_cols].values

print(f"Features prepared for clustering:")
print(f"- Number of samples (days): {X.shape[0]}")
print(f"- Number of features (time slots): {X.shape[1]}")
print(f"- Feature shape: {X.shape}")

# Check for missing values
missing_values = np.isnan(X).sum()
print(f"- Missing values: {missing_values}")

if missing_values > 0:
    print("Warning: Missing values found. Filling with mean values.")
    from sklearn.impute import SimpleImputer
    imputer = SimpleImputer(strategy='mean')
    X = imputer.fit_transform(X)
    print(f"Missing values after imputation: {np.isnan(X).sum()}")
"""))
    
    # Train StandardScaler cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Train StandardScaler
print("Training StandardScaler...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("StandardScaler trained successfully!")
print(f"Scaled data shape: {X_scaled.shape}")
print(f"Scaled data mean: {X_scaled.mean():.6f} (should be ~0)")
print(f"Scaled data std: {X_scaled.std():.6f} (should be ~1)")

# Save scaler
with open(MODELS_DIR / "profile_scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

print(f"Scaler saved to: {MODELS_DIR / 'profile_scaler.pkl'}")
"""))
    
    # Find optimal K for K-Means cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Find optimal K for K-Means
print("Testing K values from 2 to 10...")

k_range = range(2, 11)
silhouette_scores = []
davies_bouldin_scores = []

for k in k_range:
    print(f"Testing K={k}...", end=" ")
    
    # Fit K-Means
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=20)
    labels = kmeans.fit_predict(X_scaled)
    
    # Calculate metrics
    sil_score = silhouette_score(X_scaled, labels)
    db_score = davies_bouldin_score(X_scaled, labels)
    
    silhouette_scores.append(sil_score)
    davies_bouldin_scores.append(db_score)
    
    print(f"Silhouette: {sil_score:.4f}, DBI: {db_score:.4f}")

# Find best K based on silhouette score
best_k_idx = np.argmax(silhouette_scores)
best_k = k_range[best_k_idx]
best_silhouette = silhouette_scores[best_k_idx]
best_dbi = davies_bouldin_scores[best_k_idx]

print(f"\\nBest K selected: {best_k}")
print(f"Silhouette Score: {best_silhouette:.4f}")
print(f"Davies-Bouldin Index: {best_dbi:.4f}")
"""))
    
    # Train final K-Means cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Train final K-Means model
print(f"Training final K-Means model with K={best_k}...")

kmeans_final = KMeans(n_clusters=best_k, random_state=42, n_init=20)
kmeans_labels = kmeans_final.fit_predict(X_scaled)

# Analyze cluster distribution
unique_labels, counts = np.unique(kmeans_labels, return_counts=True)
cluster_distribution = dict(zip(unique_labels, counts))

print(f"K-Means model trained successfully!")
print(f"\\nCluster distribution:")
for cluster_id, count in sorted(cluster_distribution.items()):
    percentage = count / len(kmeans_labels) * 100
    print(f"Cluster {cluster_id}: {count} days ({percentage:.1f}%)")

# Save K-Means model
with open(MODELS_DIR / "kmeans_model.pkl", "wb") as f:
    pickle.dump(kmeans_final, f)

print(f"K-Means model saved to: {MODELS_DIR / 'kmeans_model.pkl'}")
"""))
    
    # Train DBSCAN cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Train DBSCAN model
print("Training DBSCAN model...")

eps_start = 1.6
min_samples = 8
eps = eps_start
dbscan = None
dbscan_labels = None

for attempt in range(10):
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    dbscan_labels = dbscan.fit_predict(X_scaled)
    
    noise_count = np.sum(dbscan_labels == -1)
    cluster_count = len(np.unique(dbscan_labels[dbscan_labels != -1]))
    
    print(f"Attempt {attempt + 1}: eps={eps:.1f}, noise_points={noise_count}, clusters={cluster_count}")
    
    if not np.all(dbscan_labels == -1):  # Not all points are noise
        break
    eps += 0.4

# Analyze DBSCAN results
noise_count = np.sum(dbscan_labels == -1)
non_noise_labels = dbscan_labels[dbscan_labels != -1]
unique_dbscan_clusters = np.unique(non_noise_labels)

print(f"\\nDBSCAN trained successfully!")
print(f"Final eps: {eps:.1f}")
print(f"Noise points: {noise_count} ({noise_count/len(dbscan_labels)*100:.1f}%)")
print(f"Number of clusters: {len(unique_dbscan_clusters)}")

# Save DBSCAN model
with open(MODELS_DIR / "dbscan_model.pkl", "wb") as f:
    pickle.dump(dbscan, f)

print(f"DBSCAN model saved to: {MODELS_DIR / 'dbscan_model.pkl'}")
"""))
    
    # Create clustering results cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Create clustering results dataframe
clustering_results = pd.DataFrame({
    'date': daily_profiles['date'],
    'kmeans_cluster': kmeans_labels,
    'dbscan_cluster': dbscan_labels,
    'dbscan_noise_flag': (dbscan_labels == -1).astype(int),
    'daily_mean': daily_profiles['daily_mean'],
    'daily_peak': daily_profiles['daily_peak'],
    'daily_std': daily_profiles['daily_std'],
    'day_of_week': daily_profiles['day_of_week'],
    'month': daily_profiles['month'],
    'is_weekend': daily_profiles['is_weekend']
})

# Save clustering results
clustering_results.to_csv(CLUSTERING_RESULTS_PATH, index=False)

print(f"Clustering results saved to: {CLUSTERING_RESULTS_PATH}")
print(f"Results shape: {clustering_results.shape}")
"""))
    
    # Save metrics cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Calculate and save clustering metrics
clustering_metrics = {
    'best_k': int(best_k),
    'silhouette_score': round(float(best_silhouette), 4),
    'davies_bouldin_index': round(float(best_dbi), 4),
    'cluster_distribution': {int(k): int(v) for k, v in cluster_distribution.items()},
    'dbscan_noise_count': int(noise_count),
    'dbscan_cluster_count': int(len(unique_dbscan_clusters)),
    'dbscan_parameters': {
        'eps': round(float(eps), 2),
        'min_samples': min_samples
    },
    'data_info': {
        'total_days': len(daily_profiles),
        'features_used': len(available_cols),
        'date_range_start': daily_profiles['date'].min(),
        'date_range_end': daily_profiles['date'].max()
    }
}

# Save metrics
with open(MODELS_DIR / "clustering_metrics.json", 'w') as f:
    json.dump(clustering_metrics, f, indent=2)

print(f"Clustering metrics saved to: {MODELS_DIR / 'clustering_metrics.json'}")

print("\\n=== CLUSTERING TRAINING SUMMARY ===")
print(f"Best K for K-Means: {best_k}")
print(f"Silhouette Score: {best_silhouette:.4f}")
print(f"Davies-Bouldin Index: {best_dbi:.4f}")
print(f"DBSCAN clusters: {len(unique_dbscan_clusters)}")
print(f"DBSCAN noise points: {noise_count}")
print(f"\\nSaved files:")
print(f"- {MODELS_DIR / 'profile_scaler.pkl'}")
print(f"- {MODELS_DIR / 'kmeans_model.pkl'}")
print(f"- {MODELS_DIR / 'dbscan_model.pkl'}")
print(f"- {CLUSTERING_RESULTS_PATH}")
print(f"- {MODELS_DIR / 'clustering_metrics.json'}")
"""))
    
    return nb

def create_notebook_04():
    """Create 04_anomaly_detection_training.ipynb"""
    nb = nbf.v4.new_notebook()
    
    # Title cell
    nb.cells.append(nbf.v4.new_markdown_cell("# Anomaly Detection Training"))
    nb.cells.append(nbf.v4.new_markdown_cell("""
This notebook trains anomaly detection models to identify unusual electricity demand patterns.

## Methods Used:
- **Isolation Forest**: Unsupervised anomaly detection with contamination=0.03
- **Z-Score**: Statistical anomaly detection using threshold=3.0
- **Combined Method**: OR logic combining both methods

## Steps:
1. Load daily profiles and clustering results
2. Load profile_scaler.pkl and scale features
3. Train Isolation Forest and save to models/isolation_forest_model.pkl
4. Calculate Z-Score anomalies
5. Combine methods and create anomaly reasons
6. Save anomaly results and metrics
"""))
    
    # Import cell
    nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
import sys
from scipy import stats

# Add project root to Python path
PROJECT_ROOT = Path().resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import sklearn components
from sklearn.ensemble import IsolationForest

# Set up paths
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DAILY_PROFILES_PATH = DATA_PROCESSED_DIR / "daily_profiles.csv"
CLUSTERING_RESULTS_PATH = DATA_PROCESSED_DIR / "clustering_results.csv"
ANOMALY_RESULTS_PATH = DATA_PROCESSED_DIR / "anomaly_results.csv"

print(f"Project root: {PROJECT_ROOT}")
print(f"Daily profiles path: {DAILY_PROFILES_PATH}")
print(f"Clustering results path: {CLUSTERING_RESULTS_PATH}")
"""))
    
    # Load data cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Load daily profiles
if not DAILY_PROFILES_PATH.exists():
    raise FileNotFoundError(f"Daily profiles not found at {DAILY_PROFILES_PATH}")

daily_profiles = pd.read_csv(DAILY_PROFILES_PATH)
print(f"Daily profiles loaded: {daily_profiles.shape}")

# Load clustering results
if not CLUSTERING_RESULTS_PATH.exists():
    raise FileNotFoundError(f"Clustering results not found at {CLUSTERING_RESULTS_PATH}")

clustering_results = pd.read_csv(CLUSTERING_RESULTS_PATH)
print(f"Clustering results loaded: {clustering_results.shape}")

# Load profile scaler
scaler_path = MODELS_DIR / "profile_scaler.pkl"
if not scaler_path.exists():
    raise FileNotFoundError(f"Scaler not found at {scaler_path}")

with open(scaler_path, "rb") as f:
    scaler = pickle.load(f)
print(f"Scaler loaded successfully")
"""))
    
    # Prepare features cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Prepare features for anomaly detection
profile_cols = [f"p{str(i).zfill(2)}" for i in range(96)]
available_cols = [col for col in profile_cols if col in daily_profiles.columns]
X = daily_profiles[available_cols].values

print(f"Features prepared:")
print(f"- Number of samples (days): {X.shape[0]}")
print(f"- Number of features (time slots): {X.shape[1]}")

# Scale features using the same scaler from clustering
X_scaled = scaler.transform(X)

print(f"Features standardized using existing scaler")
print(f"Scaled data shape: {X_scaled.shape}")
"""))
    
    # Train Isolation Forest cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Train Isolation Forest model
print("Training Isolation Forest model...")

iso_forest = IsolationForest(
    n_estimators=300,
    contamination=0.03,  # Expect 3% anomalies
    random_state=42
)

iso_forest.fit(X_scaled)

# Calculate anomaly scores and predictions
iso_anomaly_scores = -iso_forest.decision_function(X_scaled)  # Higher = more anomalous
iso_anomaly_flags = iso_forest.predict(X_scaled) == -1  # -1 indicates anomaly

print(f"Isolation Forest trained successfully!")
print(f"Anomalies detected: {iso_anomaly_flags.sum()} ({iso_anomaly_flags.mean()*100:.2f}% of data)")
print(f"Expected contamination: 3.0%")
print(f"Actual contamination: {iso_anomaly_flags.mean()*100:.2f}%")

# Save Isolation Forest model
with open(MODELS_DIR / "isolation_forest_model.pkl", "wb") as f:
    pickle.dump(iso_forest, f)

print(f"Isolation Forest model saved to: {MODELS_DIR / 'isolation_forest_model.pkl'}")
"""))
    
    # Calculate Z-Score anomalies cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Calculate Z-Score based anomaly detection
print("Calculating Z-Score based anomaly detection...")

# Calculate Z-Scores for daily statistics
peak_z_scores = np.abs(stats.zscore(daily_profiles['daily_peak'], nan_policy='omit'))
mean_z_scores = np.abs(stats.zscore(daily_profiles['daily_mean'], nan_policy='omit'))

# Define anomaly thresholds
Z_SCORE_THRESHOLD = 3.0

# Create anomaly flags
peak_z_anomaly = peak_z_scores >= Z_SCORE_THRESHOLD
mean_z_anomaly = mean_z_scores >= Z_SCORE_THRESHOLD

# Combined Z-score anomaly flag
z_score_anomaly_flags = peak_z_anomaly | mean_z_anomaly

print(f"Z-Score anomaly detection completed!")
print(f"Peak demand anomalies: {peak_z_anomaly.sum()} ({peak_z_anomaly.mean()*100:.2f}%)")
print(f"Mean demand anomalies: {mean_z_anomaly.sum()} ({mean_z_anomaly.mean()*100:.2f}%)")
print(f"Combined Z-score anomalies: {z_score_anomaly_flags.sum()} ({z_score_anomaly_flags.mean()*100:.2f}%)")
"""))
    
    # Combine anomaly methods cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Combine anomaly detection methods
print("Combining multiple anomaly detection methods...")

# Combine anomaly flags using OR logic
final_anomaly_flags = iso_anomaly_flags | z_score_anomaly_flags

print(f"Combined anomaly detection results:")
print(f"Isolation Forest anomalies: {iso_anomaly_flags.sum()} ({iso_anomaly_flags.mean()*100:.2f}%)")
print(f"Z-Score anomalies: {z_score_anomaly_flags.sum()} ({z_score_anomaly_flags.mean()*100:.2f}%)")
print(f"Final combined anomalies: {final_anomaly_flags.sum()} ({final_anomaly_flags.mean()*100:.2f}%)")

# Create anomaly reasons
anomaly_reasons = []
for i in range(len(daily_profiles)):
    reasons = []
    if iso_anomaly_flags[i]:
        reasons.append(f"Isolation Forest (score: {iso_anomaly_scores[i]:.3f})")
    if peak_z_anomaly[i]:
        reasons.append(f"Peak Z-Score ({peak_z_scores[i]:.2f})")
    if mean_z_anomaly[i]:
        reasons.append(f"Mean Z-Score ({mean_z_scores[i]:.2f})")
    anomaly_reasons.append("; ".join(reasons) if reasons else "No anomaly")

print(f"Anomaly reasons generated for all days.")
"""))
    
    # Create anomaly results cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Prepare anomaly results dataframe
anomaly_results = pd.DataFrame({
    'date': daily_profiles['date'],
    'isolation_anomaly_score': iso_anomaly_scores,
    'isolation_anomaly_flag': iso_anomaly_flags,
    'peak_z_score': peak_z_scores,
    'mean_z_score': mean_z_scores,
    'z_score_anomaly_flag': z_score_anomaly_flags,
    'final_anomaly_flag': final_anomaly_flags,
    'anomaly_reason': anomaly_reasons
})

# Merge with clustering results
anomaly_results = anomaly_results.merge(
    clustering_results[['date', 'kmeans_cluster', 'dbscan_cluster', 'dbscan_noise_flag']],
    on='date',
    how='left'
)

# Add daily statistics for analysis
anomaly_results = anomaly_results.merge(
    daily_profiles[['date', 'daily_peak', 'daily_mean', 'daily_std']],
    on='date',
    how='left'
)

print(f"Anomaly results prepared: {anomaly_results.shape}")
print(f"\\nSample of anomaly results:")
print(anomaly_results[['date', 'final_anomaly_flag', 'isolation_anomaly_score', 
                      'peak_z_score', 'mean_z_score', 'anomaly_reason']].head())
"""))
    
    # Save results and metrics cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Save anomaly results
anomaly_results.to_csv(ANOMALY_RESULTS_PATH, index=False)
print(f"Anomaly results saved to: {ANOMALY_RESULTS_PATH}")

# Calculate and save anomaly metrics
total_days = len(anomaly_results)
anomaly_metrics = {
    'total_days': total_days,
    'anomaly_days': int(final_anomaly_flags.sum()),
    'anomaly_percentage': round(float(final_anomaly_flags.mean()) * 100, 2),
    'isolation_forest_anomaly_count': int(iso_anomaly_flags.sum()),
    'z_score_anomaly_count': int(z_score_anomaly_flags.sum()),
    'final_anomaly_count': int(final_anomaly_flags.sum()),
    'isolation_forest_metrics': {
        'contamination_setting': 0.03,
        'actual_contamination': round(float(iso_anomaly_flags.mean()), 4),
        'n_estimators': 300
    },
    'z_score_metrics': {
        'threshold': Z_SCORE_THRESHOLD,
        'peak_z_anomalies': int(peak_z_anomaly.sum()),
        'mean_z_anomalies': int(mean_z_anomaly.sum())
    },
    'data_info': {
        'date_range_start': daily_profiles['date'].min(),
        'date_range_end': daily_profiles['date'].max()
    }
}

# Save metrics
with open(MODELS_DIR / "anomaly_metrics.json", 'w') as f:
    json.dump(anomaly_metrics, f, indent=2)

print(f"Anomaly metrics saved to: {MODELS_DIR / 'anomaly_metrics.json'}")

print("\\n=== ANOMALY DETECTION SUMMARY ===")
print(f"Total days analyzed: {total_days}")
print(f"Final anomalies detected: {anomaly_metrics['anomaly_days']} ({anomaly_metrics['anomaly_percentage']}%)")
print(f"Isolation Forest anomalies: {anomaly_metrics['isolation_forest_anomaly_count']}")
print(f"Z-Score anomalies: {anomaly_metrics['z_score_anomaly_count']}")
print(f"\\nSaved files:")
print(f"- {MODELS_DIR / 'isolation_forest_model.pkl'}")
print(f"- {ANOMALY_RESULTS_PATH}")
print(f"- {MODELS_DIR / 'anomaly_metrics.json'}")
"""))
    
    return nb

def create_notebook_05():
    """Create 05_behavior_label_generation.ipynb"""
    nb = nbf.v4.new_notebook()
    
    # Title cell
    nb.cells.append(nbf.v4.new_markdown_cell("# Behavior Label Generation"))
    nb.cells.append(nbf.v4.new_markdown_cell("""
This notebook generates final behavior labels by combining clustering, anomaly detection, and peak demand results.

## Behavior Labels:
- **Normal Weekday Demand**: Regular weekday consumption patterns
- **Peak Demand Day**: High demand days (90th percentile)
- **Holiday or Low Demand Day**: Weekends or low consumption days
- **Abnormal Demand Day**: Anomalous patterns that aren't normal peaks

## Risk Levels:
- **Normal**: Normal Weekday Demand
- **Low**: Holiday or Low Demand Day  
- **Medium**: Peak Demand Day
- **High**: Abnormal Demand Day

## Steps:
1. Load daily profiles, clustering results, and anomaly results
2. Detect peak demand days using 90th percentile threshold
3. Combine all results by date
4. Generate behavior labels using rule-based logic
5. Create behavior reasons and risk levels
6. Save final behavior labels and summary
"""))
    
    # Import cell
    nb.cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path().resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set up paths
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DAILY_PROFILES_PATH = DATA_PROCESSED_DIR / "daily_profiles.csv"
CLUSTERING_RESULTS_PATH = DATA_PROCESSED_DIR / "clustering_results.csv"
ANOMALY_RESULTS_PATH = DATA_PROCESSED_DIR / "anomaly_results.csv"
PEAK_DEMAND_RESULTS_PATH = DATA_PROCESSED_DIR / "peak_demand_results.csv"
BEHAVIOR_LABELS_PATH = DATA_PROCESSED_DIR / "behavior_labels.csv"

print(f"Project root: {PROJECT_ROOT}")
print(f"Daily profiles path: {DAILY_PROFILES_PATH}")
print(f"Behavior labels path: {BEHAVIOR_LABELS_PATH}")
"""))
    
    # Load all data cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Load daily profiles
if not DAILY_PROFILES_PATH.exists():
    raise FileNotFoundError(f"Daily profiles not found at {DAILY_PROFILES_PATH}")

daily_profiles = pd.read_csv(DAILY_PROFILES_PATH)
print(f"Daily profiles loaded: {daily_profiles.shape}")

# Load clustering results
if not CLUSTERING_RESULTS_PATH.exists():
    raise FileNotFoundError(f"Clustering results not found at {CLUSTERING_RESULTS_PATH}")

clustering_results = pd.read_csv(CLUSTERING_RESULTS_PATH)
print(f"Clustering results loaded: {clustering_results.shape}")

# Load anomaly results
if not ANOMALY_RESULTS_PATH.exists():
    raise FileNotFoundError(f"Anomaly results not found at {ANOMALY_RESULTS_PATH}")

anomaly_results = pd.read_csv(ANOMALY_RESULTS_PATH)
print(f"Anomaly results loaded: {anomaly_results.shape}")

print(f"\\nData loaded successfully!")
print(f"Date range: {daily_profiles['date'].min()} to {daily_profiles['date'].max()}")
"""))
    
    # Detect peak demand days cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Detect peak demand days using 90th percentile threshold
print("Detecting peak demand days...")

# Calculate 90th percentile threshold
peak_threshold_90 = daily_profiles['daily_peak'].quantile(0.90)
peak_threshold_75 = daily_profiles['daily_peak'].quantile(0.75)

print(f"90th percentile threshold: {peak_threshold_90:.2f} kW")
print(f"75th percentile threshold: {peak_threshold_75:.2f} kW")

# Apply peak detection logic
cond_90 = daily_profiles['daily_peak'] >= peak_threshold_90
cond_anomaly = anomaly_results['final_anomaly_flag'] & (daily_profiles['daily_peak'] >= peak_threshold_75)

is_peak_demand_day = cond_90 | cond_anomaly

# Generate peak reasons
peak_reasons = []
for i in range(len(daily_profiles)):
    reasons = []
    if cond_90.iloc[i]:
        reasons.append(f"daily_peak >= 90th percentile ({peak_threshold_90:.1f} kW)")
    if cond_anomaly.iloc[i]:
        reasons.append(f"anomaly with daily_peak >= 75th percentile ({peak_threshold_75:.1f} kW)")
    peak_reasons.append("; ".join(reasons) if reasons else "not a peak day")

# Create peak demand results
peak_results = daily_profiles[['date', 'daily_peak', 'daily_mean']].copy()
peak_results['peak_threshold'] = peak_threshold_90
peak_results['is_peak_demand_day'] = is_peak_demand_day.values
peak_results['peak_reason'] = peak_reasons

# Save peak demand results
peak_results.to_csv(PEAK_DEMAND_RESULTS_PATH, index=False)

print(f"Peak demand results saved to: {PEAK_DEMAND_RESULTS_PATH}")
print(f"Peak days identified: {is_peak_demand_day.sum()}")
print(f"Peak percentage: {is_peak_demand_day.mean()*100:.2f}%")
"""))
    
    # Combine all results cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Combine all results by date
print("Combining all results by date...")

# Start with daily profiles
behavior_data = daily_profiles[['date', 'daily_mean', 'daily_peak', 'daily_std', 
                              'day_of_week', 'month', 'is_weekend']].copy()

# Merge clustering results
behavior_data = behavior_data.merge(
    clustering_results[['date', 'kmeans_cluster', 'dbscan_cluster', 'dbscan_noise_flag']],
    on='date', how='left'
)

# Merge anomaly results
behavior_data = behavior_data.merge(
    anomaly_results[['date', 'final_anomaly_flag', 'anomaly_reason']],
    on='date', how='left'
)

# Merge peak demand results
behavior_data = behavior_data.merge(
    peak_results[['date', 'is_peak_demand_day', 'peak_reason']],
    on='date', how='left'
)

print(f"Combined data shape: {behavior_data.shape}")
print(f"\\nCombined data columns: {list(behavior_data.columns)}")
"""))
    
    # Generate behavior labels cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Calculate low demand threshold
low_threshold = behavior_data['daily_mean'].quantile(0.25)
print(f"Low demand threshold (25th percentile): {low_threshold:.2f} kW")

# Generate behavior labels
print("Generating behavior labels...")

labels = []
reasons = []
risk_levels = []

for _, row in behavior_data.iterrows():
    is_anomaly = bool(row['final_anomaly_flag'])
    is_peak = bool(row['is_peak_demand_day'])
    is_weekend = bool(row['is_weekend'])
    is_low = row['daily_mean'] < low_threshold
    
    if is_anomaly and not is_peak:
        label = "Abnormal Demand Day"
        risk = "High"
        reason = f"Flagged as anomaly ({row['anomaly_reason']}) but not a peak day"
    elif is_peak:
        label = "Peak Demand Day"
        risk = "Medium"
        reason = f"Peak day triggered: {row['peak_reason']}"
    elif is_weekend or is_low:
        label = "Holiday / Low Demand Day"
        risk = "Low"
        reason = f"Weekend or low demand (mean: {row['daily_mean']:.1f} kW < threshold: {low_threshold:.1f} kW)"
    else:
        label = "Normal Weekday Demand"
        risk = "Normal"
        reason = f"Normal demand pattern (mean: {row['daily_mean']:.1f} kW)"
    
    labels.append(label)
    reasons.append(reason)
    risk_levels.append(risk)

# Add labels to dataframe
behavior_data['behavior_label'] = labels
behavior_data['behavior_reason'] = reasons
behavior_data['behavior_risk_level'] = risk_levels

print("Behavior labels generated successfully!")
"""))
    
    # Analyze and save results cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Calculate label distribution
total_days = len(behavior_data)
label_counts = behavior_data['behavior_label'].value_counts().to_dict()
label_percentages = {k: round(v / total_days * 100, 2) for k, v in label_counts.items()}

print("=== BEHAVIOR LABEL DISTRIBUTION ===")
for label, count in label_counts.items():
    print(f"{label}: {count} days ({label_percentages[label]}%)")

# Calculate risk distribution
risk_counts = behavior_data['behavior_risk_level'].value_counts().to_dict()
risk_percentages = {k: round(v / total_days * 100, 2) for k, v in risk_counts.items()}

print("\\n=== RISK LEVEL DISTRIBUTION ===")
for risk, count in risk_counts.items():
    print(f"{risk}: {count} days ({risk_percentages[risk]}%)")

# Save behavior labels
behavior_data.to_csv(BEHAVIOR_LABELS_PATH, index=False)

print(f"\\nBehavior labels saved to: {BEHAVIOR_LABELS_PATH}")
print(f"Final shape: {behavior_data.shape}")
"""))
    
    # Save summary metrics cell
    nb.cells.append(nbf.v4.new_code_cell("""
# Create and save behavior summary
behavior_summary = {
    'total_days': total_days,
    'label_counts': label_counts,
    'label_percentages': label_percentages,
    'risk_distribution': risk_counts,
    'risk_percentages': risk_percentages,
    'low_demand_threshold': round(float(low_threshold), 2),
    'peak_demand_threshold_90': round(float(peak_threshold_90), 2),
    'peak_demand_threshold_75': round(float(peak_threshold_75), 2),
    'peak_days_count': int(is_peak_demand_day.sum()),
    'peak_days_percentage': round(float(is_peak_demand_day.mean()) * 100, 2),
    'anomaly_days_count': int(behavior_data['final_anomaly_flag'].sum()),
    'anomaly_days_percentage': round(float(behavior_data['final_anomaly_flag'].mean()) * 100, 2),
    'data_info': {
        'date_range_start': behavior_data['date'].min(),
        'date_range_end': behavior_data['date'].max(),
        'weekend_days': int(behavior_data['is_weekend'].sum()),
        'weekday_days': int((~behavior_data['is_weekend']).sum())
    }
}

# Save summary
with open(MODELS_DIR / "behavior_label_summary.json", 'w') as f:
    json.dump(behavior_summary, f, indent=2)

print(f"Behavior summary saved to: {MODELS_DIR / 'behavior_label_summary.json'}")

print("\\n=== FINAL BEHAVIOR LABELING SUMMARY ===")
print(f"Total days analyzed: {total_days}")
print(f"Date range: {behavior_data['date'].min()} to {behavior_data['date'].max()}")
print(f"Peak demand days: {behavior_summary['peak_days_count']} ({behavior_summary['peak_days_percentage']}%)")
print(f"Anomaly days: {behavior_summary['anomaly_days_count']} ({behavior_summary['anomaly_days_percentage']}%)")
print(f"\\nSaved files:")
print(f"- {BEHAVIOR_LABELS_PATH}")
print(f"- {PEAK_DEMAND_RESULTS_PATH}")
print(f"- {MODELS_DIR / 'behavior_label_summary.json'}")
"""))
    
    return nb

def main():
    """Main function to recreate all notebooks"""
    print("Recreating all Jupyter notebooks...")
    
    notebooks_dir = PROJECT_ROOT / "notebooks"
    notebooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Create each notebook
    notebook_creators = [
        ("01_data_preprocessing.ipynb", create_notebook_01),
        ("02_daily_profile_generation.ipynb", create_notebook_02),
        ("03_clustering_model_training.ipynb", create_notebook_03),
        ("04_anomaly_detection_training.ipynb", create_notebook_04),
        ("05_behavior_label_generation.ipynb", create_notebook_05)
    ]
    
    for filename, creator in notebook_creators:
        try:
            print(f"Creating {filename}...")
            nb = creator()
            
            # Validate notebook
            nbf.validate(nb)
            
            # Write notebook
            notebook_path = notebooks_dir / filename
            nbf.write(nb, notebook_path)
            
            print(f"Recreated notebooks/{filename}")
            
        except Exception as e:
            print(f"Error creating {filename}: {str(e)}")
            return False
    
    print("\\nAll notebooks recreated successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
