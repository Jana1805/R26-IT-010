# Behavior Intelligence Training Pipeline Summary

## Overview

This document provides a comprehensive guide for training the Behavior Intelligence Module for electricity demand analysis. The training pipeline processes raw electricity demand data and generates behavior classifications using machine learning techniques.

## Project Structure

```
behaviour-intelligence/
├── backend/app/ml/           # ML pipeline components
├── notebooks/                 # Jupyter notebooks for step-by-step training
├── data/
│   ├── raw/                  # Raw dataset (CSV files)
│   └── processed/           # Generated processed data
├── models/                   # Trained ML models (.pkl files)
├── reports/                  # Documentation and summaries
└── requirements.txt          # Python dependencies
```

## Training Pipeline Steps

### Step 1: Data Preprocessing
**File**: `notebooks/01_data_preprocessing.ipynb`

- Load raw electricity demand dataset
- Auto-detect timestamp and demand columns
- Remove invalid values and outliers
- Resample to 15-minute intervals
- Add time-based features
- Save cleaned data

**Output**: `data/processed/cleaned_data.csv`

### Step 2: Daily Profile Generation
**File**: `notebooks/02_daily_profile_generation.ipynb`

- Convert time series to daily 96-slot profiles
- Calculate daily statistics (peak, mean, std, min)
- Identify peak time slots
- Add temporal features
- Filter incomplete days

**Output**: `data/processed/daily_profiles.csv`

### Step 3: Clustering Model Training
**File**: `notebooks/03_clustering_model_training.ipynb`

- Standardize profile features
- Test K-Means with K=2 to 10
- Select optimal K using Silhouette Score
- Train K-Means and DBSCAN models
- Evaluate clustering performance

**Outputs**: 
- `models/kmeans_model.pkl`
- `models/dbscan_model.pkl`
- `models/profile_scaler.pkl`
- `models/clustering_metrics.json`
- `data/processed/clustering_results.csv`

### Step 4: Anomaly Detection Training
**File**: `notebooks/04_anomaly_detection_training.ipynb`

- Train Isolation Forest model
- Calculate Z-Score based anomalies
- Combine multiple detection methods
- Analyze anomaly patterns

**Outputs**:
- `models/isolation_forest_model.pkl`
- `models/anomaly_metrics.json`
- `data/processed/anomaly_results.csv`

### Step 5: Behavior Label Generation
**File**: `notebooks/05_behavior_label_generation.ipynb`

- Detect peak demand days using percentiles
- Apply rule-based behavior labeling
- Assign risk levels to behaviors
- Generate comprehensive analysis

**Outputs**:
- `data/processed/behavior_labels.csv`
- `data/processed/peak_demand_results.csv`
- `models/behavior_label_summary.json`

## Quick Start: Complete Training

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Raw Data**:
   - Ensure `data/raw/load_forecasting_dataset_corrected.csv` exists
   - Dataset should contain timestamp and demand columns

### Run Complete Training Pipeline

Execute the complete training pipeline with a single command:

```bash
python backend/app/ml/train_models.py
```

This script will:
1. Run all 8 training steps automatically
2. Create all necessary directories
3. Generate all processed data files
4. Train and save all ML models
5. Calculate and save evaluation metrics
6. Provide comprehensive progress updates

### Expected Output

The training pipeline will generate:

#### Processed Data Files
- `data/processed/cleaned_data.csv` - Cleaned time series data
- `data/processed/daily_profiles.csv` - Daily 96-slot profiles
- `data/processed/clustering_results.csv` - Cluster assignments
- `data/processed/anomaly_results.csv` - Anomaly detection results
- `data/processed/peak_demand_results.csv` - Peak demand identification
- `data/processed/behavior_labels.csv` - Final behavior classifications

#### Trained Models
- `models/profile_scaler.pkl` - Feature standardization scaler
- `models/kmeans_model.pkl` - K-Means clustering model
- `models/dbscan_model.pkl` - DBSCAN clustering model
- `models/isolation_forest_model.pkl` - Anomaly detection model

#### Evaluation Metrics
- `models/clustering_metrics.json` - Clustering performance metrics
- `models/anomaly_metrics.json` - Anomaly detection statistics
- `models/behavior_label_summary.json` - Behavior analysis summary

## Behavior Classification System

The system classifies each day into one of four behavior types:

### 1. Normal Weekday Demand
- **Risk Level**: Normal
- **Characteristics**: Regular consumption patterns
- **Typical**: Standard weekday electricity usage

### 2. Peak Demand Day
- **Risk Level**: Medium
- **Characteristics**: High consumption (≥90th percentile)
- **Detection**: Peak demand threshold or anomaly + high demand

### 3. Abnormal Demand Day
- **Risk Level**: High
- **Characteristics**: Unusual patterns not explained by peak demand
- **Detection**: Anomaly detected but not classified as peak

### 4. Holiday / Low Demand Day
- **Risk Level**: Low
- **Characteristics**: Reduced consumption patterns
- **Detection**: Weekend or low demand (<25th percentile)

## Model Evaluation Metrics

### Clustering Metrics
- **Silhouette Score**: Measures cluster separation (-1 to 1, higher is better)
- **Davies-Bouldin Index**: Measures cluster similarity (lower is better)
- **Cluster Distribution**: Number of days per cluster

### Anomaly Detection Metrics
- **Anomaly Rate**: Percentage of days flagged as anomalous
- **Method Overlap**: Agreement between different detection methods
- **Temporal Patterns**: Anomaly distribution by time periods

### Behavior Analysis Metrics
- **Label Distribution**: Percentage of each behavior type
- **Risk Distribution**: Overall risk level breakdown
- **Temporal Analysis**: Behavior patterns by day/week/month

## Running the System

### After Training

Once training is complete, start the system:

1. **Start Backend API**:
   ```bash
   uvicorn backend.app.main:app --reload --port 8001
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Access Dashboard**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs

### API Endpoints

The system provides the following key endpoints:

- `POST /api/generate-daily-profiles` - Run data preprocessing
- `POST /api/run-clustering` - Train clustering models
- `POST /api/run-anomaly-detection` - Run anomaly detection
- `POST /api/detect-peak-days` - Identify peak demand days
- `POST /api/generate-behavior-labels` - Generate behavior classifications
- `GET /api/dashboard-summary` - Get dashboard data
- `GET /api/predict-future-behavior` - Predict behavior for future date
- `GET /api/get-day-profile` - Get detailed profile for specific date

## Data Requirements

### Input Data Format

The raw dataset should be a CSV file with:
- **Timestamp Column**: Date/time values (various formats supported)
- **Demand Column**: Electricity consumption in kW
- **Optional**: Additional features (temperature, humidity, etc.)

### Expected Data Characteristics

- **Time Resolution**: Raw data can be any resolution (will be resampled to 15-min)
- **Time Period**: Minimum several months for meaningful patterns
- **Data Quality**: Some missing values acceptable (will be interpolated)
- **File Size**: Typically 10-100MB for multi-year datasets

## Troubleshooting

### Common Issues

1. **Memory Errors**:
   - Reduce dataset size or increase system memory
   - Ensure sufficient disk space for processed files

2. **Column Detection Errors**:
   - Verify CSV contains timestamp and demand columns
   - Check column names contain expected keywords (time, date, load, demand)

3. **Training Failures**:
   - Ensure all dependencies are installed
   - Check file permissions for data and model directories
   - Verify raw data format and integrity

### Performance Tips

- **SSD Storage**: Use SSD for faster I/O operations
- **Memory**: 8GB+ RAM recommended for large datasets
- **CPU**: Multi-core processor speeds up training significantly

## Model Retraining

### When to Retrain

- **New Data**: Add significant new time periods (6+ months)
- **Pattern Changes**: Consumption patterns change significantly
- **Performance Degradation**: Model accuracy decreases over time

### Retraining Process

1. Backup existing models and data
2. Add new raw data to `data/raw/` directory
3. Run training pipeline: `python backend/app/ml/train_models.py`
4. Validate new model performance
5. Update system if performance improved

## Advanced Usage

### Custom Parameters

Modify training parameters in `backend/app/ml/train_models.py`:

- **Clustering**: Adjust K range, DBSCAN parameters
- **Anomaly Detection**: Change contamination rate, Z-score thresholds
- **Peak Detection**: Modify percentile thresholds
- **Behavior Rules**: Update labeling logic and risk assignments

### Jupyter Notebook Usage

For detailed analysis and experimentation:

1. Start Jupyter: `jupyter notebook`
2. Open notebooks in `notebooks/` directory
3. Run cells sequentially
4. Modify parameters and re-run as needed

## Support

For issues and questions:

1. Check this documentation first
2. Review error messages in training output
3. Examine generated metrics files
4. Validate input data format and quality

---

**Last Updated**: 2025-01-11  
**Version**: 1.0.0  
**Author**: Behavior Intelligence Development Team
