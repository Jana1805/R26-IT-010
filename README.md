# AI-Based Electricity Demand Behaviour Intelligence System

**Student:** Thanujan T — IT22545176  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Supervisor:** Dr. Nathali Silva

## About

This system applies machine learning and behavioural analytics to model, classify, and forecast electricity demand patterns at the consumer level. By analysing historical consumption data alongside contextual features such as time-of-day, day-of-week, seasonality, and appliance usage profiles, the system identifies distinct demand behaviour archetypes and generates short-term load forecasts. The insights produced enable utility providers and energy managers to optimise load scheduling, reduce peak-demand stress on the grid, and support data-driven demand-response strategies — ultimately contributing to a smarter, more efficient electricity distribution network.

## Quick Start

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Raw Data**:
   - Ensure `data/raw/load_forecasting_dataset_corrected.csv` exists
   - Dataset should contain timestamp and demand columns

### Train the ML Models

Run the complete training pipeline with a single command:

```bash
python backend/app/ml/train_models.py
```

This will:
- Process raw electricity demand data
- Train clustering and anomaly detection models
- Generate behavior classifications
- Save all models and processed data

### Start the System

After training completes:

1. **Start Backend API**:
   ```bash
   cd D:\Y4S1\Research\Component1-Behaviour-Intelligence\behaviour-intelligence
   python -m uvicorn backend.app.main:app --reload --port 8001
   ```

2. **Start Frontend**:
   ```bash
   cd D:\Y4S1\Research\Component1-Behaviour-Intelligence\behaviour-intelligence\frontend
   npm start
   ```

### Backend API Access

- **API Base URL**: http://127.0.0.1:8001
- **API Documentation**: http://127.0.0.1:8001/docs
- **Health Check**: http://127.0.0.1:8001/health

### Important Notes

- Always run backend from project root (`behaviour-intelligence/` directory)
- Do not run from `backend/` or `backend/app/` subdirectories
- The backend will automatically detect and use absolute paths for data and models

3. **Access Dashboard**:
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8001/docs

## Training Pipeline

The system includes a comprehensive 8-step training pipeline:

1. **Data Preprocessing** - Clean and resample raw data
2. **Daily Profile Generation** - Create 96-slot daily profiles
3. **Clustering Training** - K-Means and DBSCAN models
4. **Anomaly Detection** - Isolation Forest and Z-score methods
5. **Peak Demand Detection** - Percentile-based identification
6. **Behavior Labeling** - Rule-based classification
7. **Model Evaluation** - Performance metrics and analysis
8. **Results Generation** - Final outputs and summaries

### Behavior Classification

Each day is classified into one of four behavior types:

- **Normal Weekday Demand** (Normal Risk) - Regular consumption patterns
- **Peak Demand Day** (Medium Risk) - High consumption days
- **Abnormal Demand Day** (High Risk) - Unusual patterns
- **Holiday / Low Demand Day** (Low Risk) - Reduced consumption

## Project Structure

```
behaviour-intelligence/
├── backend/app/ml/           # ML pipeline components
├── notebooks/                 # Step-by-step training notebooks
├── data/
│   ├── raw/                  # Raw dataset
│   └── processed/           # Generated processed data
├── models/                   # Trained ML models
├── reports/                  # Documentation
└── frontend/                 # React dashboard
```

## Detailed Documentation

For comprehensive training instructions and technical details, see:
- [`reports/training_pipeline_summary.md`](reports/training_pipeline_summary.md) - Complete training guide
- [`notebooks/`](notebooks/) - Step-by-step Jupyter notebooks

## Key Features

- **Automated Data Processing**: Handles raw electricity demand data
- **Machine Learning Models**: K-Means, DBSCAN, Isolation Forest
- **Behavior Classification**: Rule-based labeling with risk assessment
- **Interactive Dashboard**: Real-time visualization and analysis
- **Future Prediction**: Historical pattern-based forecasting
- **Comprehensive Metrics**: Model evaluation and performance tracking

## ML Training and PKL Model Outputs

### Training Commands

**Complete Training Pipeline:**
```bash
python backend/app/ml/train_models.py
```

**Model Verification:**
```bash
python backend/app/ml/verify_pkl_models.py
```

### Expected Model Files

The training pipeline generates the following PKL model files:

- **models/profile_scaler.pkl** - StandardScaler for 96-point daily profiles
- **models/kmeans_model.pkl** - K-Means clustering model
- **models/dbscan_model.pkl** - DBSCAN clustering model  
- **models/isolation_forest_model.pkl** - Isolation Forest anomaly detection model

### Generated Outputs

**Processed Data Files:**
- `data/processed/cleaned_data.csv` - Cleaned time series data
- `data/processed/daily_profiles.csv` - 96-slot daily profiles
- `data/processed/clustering_results.csv` - Cluster assignments
- `data/processed/anomaly_results.csv` - Anomaly detection results
- `data/processed/peak_demand_results.csv` - Peak demand identification
- `data/processed/behavior_labels.csv` - Final behavior classifications

**Model Metrics:**
- `models/clustering_metrics.json` - Clustering performance metrics
- `models/anomaly_metrics.json` - Anomaly detection statistics
- `models/behavior_label_summary.json` - Behavior analysis summary

**Documentation:**
- `reports/model_training_outputs.md` - Detailed model training report
- `models/model_file_verification.json` - Model verification status
