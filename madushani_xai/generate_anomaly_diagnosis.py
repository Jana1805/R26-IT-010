"""
Generates anomaly_diagnosis.json for the LIME Anomaly Diagnosis component.
Run from anywhere — paths are resolved relative to this script's location.
"""
import pandas as pd
import numpy as np
import joblib
import json
import os
import warnings

warnings.filterwarnings('ignore')

try:
    import lime
    import lime.lime_tabular
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'lime'])
    import lime
    import lime.lime_tabular

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, 'backend', 'outputs')
MODEL_PATH   = os.path.join(OUTPUT_DIR, 'xgb_model.pkl')
DATASET_PATH = os.path.join(
    SCRIPT_DIR, '..', 'behaviour-intelligence', 'data', 'raw',
    'load_forecasting_dataset_corrected.csv'
)
DATASET_PATH = os.path.normpath(DATASET_PATH)

print(f'Output dir  : {OUTPUT_DIR}')
print(f'Model path  : {MODEL_PATH}  exists={os.path.exists(MODEL_PATH)}')
print(f'Dataset     : {DATASET_PATH}  exists={os.path.exists(DATASET_PATH)}')

model = joblib.load(MODEL_PATH)
print(f'Model loaded: {type(model).__name__}')

df = pd.read_csv(DATASET_PATH)
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df = df.sort_values('Timestamp').reset_index(drop=True)

target_col   = 'Load Demand (kW)'
feature_cols = [
    'Temperature (°C)', 'Humidity (%)', 'Wind Speed (m/s)', 'Rainfall (mm)',
    'Solar Irradiance (W/m²)', 'GDP (LKR)', 'Per Capita Energy Use (kWh)',
    'Electricity Price (LKR/kWh)', 'Day of Week', 'Hour of Day', 'Month', 'Public Event'
]
feature_names = [
    'Temperature', 'Humidity', 'Wind Speed', 'Rainfall', 'Solar Irradiance',
    'GDP', 'Per Capita Energy Use', 'Electricity Price',
    'Day of Week', 'Hour of Day', 'Month', 'Public Event'
]

Q1  = df[target_col].quantile(0.25)
Q3  = df[target_col].quantile(0.75)
IQR = Q3 - Q1
df_clean = df[
    (df[target_col] >= Q1 - 1.5 * IQR) &
    (df[target_col] <= Q3 + 1.5 * IQR)
].copy().reset_index(drop=True)
print(f'Rows after outlier removal: {len(df_clean):,}')

p25 = df_clean[target_col].quantile(0.25)
p75 = df_clean[target_col].quantile(0.75)
p90 = df_clean[target_col].quantile(0.90)

def get_demand_level(v):
    if v < p25:  return 'low'
    if v < p75:  return 'medium'
    if v < p90:  return 'high'
    return 'peak'

low_idx    = df_clean[df_clean[target_col] <  p25].sample(3, random_state=42).index.tolist()
medium_idx = df_clean[(df_clean[target_col] >= p25) & (df_clean[target_col] < p75)].sample(4, random_state=42).index.tolist()
high_idx   = df_clean[(df_clean[target_col] >= p75) & (df_clean[target_col] < p90)].sample(4, random_state=42).index.tolist()
peak_idx   = df_clean[df_clean[target_col] >= p90].sample(4, random_state=42).index.tolist()
selected_indices = low_idx + medium_idx + high_idx + peak_idx
df_selected = df_clean.loc[selected_indices].copy()
print(f'Selected {len(df_selected)} instances (3 low · 4 medium · 4 high · 4 peak)')

X_background = df_clean.sample(2000, random_state=42)[feature_cols].copy()
X_background.columns = feature_names
print('Building LIME explainer...')
explainer = lime.lime_tabular.LimeTabularExplainer(
    training_data=X_background.values,
    feature_names=feature_names,
    mode='regression',
    random_state=42,
    verbose=False
)
print('LIME explainer ready')

def predict_fn(X):
    return model.predict(pd.DataFrame(X, columns=feature_names))

instances_output = []
print(f'Running LIME on {len(df_selected)} instances...')

for i, (df_idx, row) in enumerate(df_selected.iterrows()):
    instance_vals = row[feature_cols].values.astype(float)
    actual        = float(row[target_col])
    predicted     = float(model.predict(pd.DataFrame([instance_vals], columns=feature_names))[0])
    error_kw      = round(predicted - actual, 4)
    error_pct     = round(abs(error_kw / actual) * 100, 4) if actual != 0 else 0.0

    exp       = explainer.explain_instance(instance_vals, predict_fn, num_features=len(feature_names), num_samples=1000)
    lime_r2   = round(float(exp.score), 4)
    intercept_raw = exp.intercept
    intercept = round(float(list(intercept_raw.values())[0] if isinstance(intercept_raw, dict) else intercept_raw), 4)

    # Regression mode: real weights are under key 1 (key 0 is a negated copy).
    # as_list() gives the same weights in the same order, with the rule text.
    raw_contribs  = exp.local_exp[1]
    rules         = {fi: rule for (fi, _), (rule, _) in zip(raw_contribs, exp.as_list(label=1))}
    contributions = [
        {'feature': feature_names[fi], 'rule': rules[fi], 'weight': round(float(w), 4), 'value': round(float(instance_vals[fi]), 4)}
        for fi, w in sorted(raw_contribs, key=lambda x: abs(x[1]), reverse=True)
    ]
    local_pred    = round(float(exp.local_pred[0]), 4)

    instances_output.append({
        'id'           : i + 1,
        'timestamp'    : str(row['Timestamp']),
        'actual'       : round(actual, 2),
        'predicted'    : round(predicted, 2),
        'error_kw'     : error_kw,
        'error_pct'    : error_pct,
        'demand_level' : get_demand_level(actual),
        'lime_r2'      : lime_r2,
        'intercept'    : intercept,
        'local_pred'   : local_pred,
        'contributions': contributions,
        'feature_values': {feature_names[j]: round(float(instance_vals[j]), 4) for j in range(len(feature_names))}
    })
    print(f'  [{i+1:02d}/{len(df_selected)}] {get_demand_level(actual):6s} | actual={actual:8.2f} | predicted={predicted:8.2f} | R²={lime_r2:.3f}')

output = {
    'instances': instances_output,
    'meta': {
        'sample_count'  : len(instances_output),
        'mean_demand'   : round(float(df_clean[target_col].mean()), 2),
        'std_demand'    : round(float(df_clean[target_col].std()),  2),
        'p25_threshold' : round(float(p25), 2),
        'p75_threshold' : round(float(p75), 2),
        'p90_threshold' : round(float(p90), 2)
    }
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
json_path = os.path.join(OUTPUT_DIR, 'anomaly_diagnosis.json')
with open(json_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f'\nSaved: {json_path}')
print('Done.')
