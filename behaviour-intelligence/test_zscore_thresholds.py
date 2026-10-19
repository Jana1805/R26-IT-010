import pandas as pd
from scipy import stats

df = pd.read_csv('data/processed/daily_profiles.csv')
peak_z = stats.zscore(df['peak_demand'], nan_policy='omit')
mean_z = stats.zscore(df['mean_demand'], nan_policy='omit')

for thresh in [3.0, 2.5, 2.0]:
    iso = (abs(peak_z) >= thresh) | (abs(mean_z) >= thresh)
    print(f'Threshold {thresh}: {iso.sum()} anomalies ({iso.mean()*100:.2f}%)')
