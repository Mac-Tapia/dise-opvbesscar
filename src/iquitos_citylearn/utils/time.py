from __future__ import annotations
import numpy as np
import pandas as pd

def year_index(year: int, step_minutes: int) -> pd.DatetimeIndex:
    periods = int(365 * 24 * 60 / step_minutes)
    return pd.date_range(f"{year}-01-01", periods=periods, freq=f"{step_minutes}min")

def day_type_from_index(idx: pd.DatetimeIndex) -> np.ndarray:
    # 1..7 (Mon..Sun)
    idx_series = idx.to_series()
    return (idx_series.dt.dayofweek.to_numpy() + 1).astype(int)
