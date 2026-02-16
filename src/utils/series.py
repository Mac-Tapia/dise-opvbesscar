from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

def read_first_numeric_csv(path: str | Path) -> pd.Series:
    df = pd.read_csv(path)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        raise ValueError(f"No numeric columns found in {path}")
    return df[num_cols[0]].astype(float)

def repeat_to_length(x: np.ndarray, n: int) -> np.ndarray:
    if len(x) == n:
        return x
    reps = int(np.ceil(n / len(x)))
    return np.tile(x, reps)[:n]

def to_csv_1col(path: str | Path, name: str, values: np.ndarray) -> None:
    pd.DataFrame({name: values}).to_csv(path, index=False)
