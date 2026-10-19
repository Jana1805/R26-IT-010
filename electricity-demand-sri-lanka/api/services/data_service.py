"""Dataset loading for data-backed API endpoints."""
from pathlib import Path
import pandas as pd
from api.core.config import DATA_PATH
from api.services.feature_engineering import engineer_features

class DataLoadError(RuntimeError):
    pass

def load_data(data_path:Path=DATA_PATH)->pd.DataFrame:
    try:
        frame=pd.read_csv(data_path,parse_dates=["Timestamp"])
        frame=frame.sort_values("Timestamp").set_index("Timestamp")
        frame=engineer_features(frame)
        if frame.empty: raise ValueError("no usable rows after feature engineering")
        return frame
    except Exception as exc:
        raise DataLoadError("Dataset could not be loaded or feature-engineered") from exc
