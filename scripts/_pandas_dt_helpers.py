"""
Helpers robustos para operaciones pandas .dt sin errores Pylance.

PROBLEMA: Pylance 1.1.359+ reporta que atributos .dt.* no existen aunque sí están.
SOLUCIÓN: Wrappers explícitos que mantienen tipos claros para Pylance.

Uso:
    from _pandas_dt_helpers import extract_hour, extract_day_name, extract_date

    df['hora'] = extract_hour(df['fechahora'])
    df['dia_semana'] = extract_day_name(df['fechahora'])
    df['fecha'] = extract_date(df['fechahora'])
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any

def extract_hour(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract hour from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.hour
    return result.astype(int)  # type: ignore

def extract_minute(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract minute from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.minute
    return result.astype(int)  # type: ignore

def extract_day(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract day from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.day
    return result.astype(int)  # type: ignore

def extract_month(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract month from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.month
    return result.astype(int)  # type: ignore

def extract_year(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract year from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.year
    return result.astype(int)  # type: ignore

def extract_date(series: pd.Series[Any] | pd.Series) -> pd.Series[str]:
    """Extract date from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.date
    return result.astype(str)  # type: ignore

def extract_day_name(series: pd.Series[Any] | pd.Series) -> pd.Series[str]:
    """Extract day name from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.day_name()
    return result.astype(str)  # type: ignore

def extract_dayofweek(series: pd.Series[Any] | pd.Series) -> pd.Series[int]:
    """Extract day of week from datetime Series with explicit typing."""
    result = pd.to_datetime(series).dt.dayofweek
    return result.astype(int)  # type: ignore

def extract_floor_hour(series: pd.Series[Any] | pd.Series) -> pd.Series:
    """Floor datetime to hour with explicit typing."""
    return pd.to_datetime(series).dt.floor('h')  # type: ignore

def extract_values_float(series: pd.Series[Any] | pd.Series | Any) -> np.ndarray:
    """Extract values as float array with explicit typing."""
    if isinstance(series, pd.Series):
        return np.array(series.values, dtype=float)  # type: ignore
    elif hasattr(series, '__iter__'):
        return np.array(series, dtype=float)  # type: ignore
    else:
        return np.array([series], dtype=float)  # type: ignore

def extract_values_str(series: pd.Series[Any] | pd.Series | Any) -> np.ndarray:
    """Extract values as string array with explicit typing."""
    if isinstance(series, pd.Series):
        return np.array(series.values, dtype=str)  # type: ignore
    elif hasattr(series, '__iter__'):
        return np.array(series, dtype=str)  # type: ignore
    else:
        return np.array([series], dtype=str)  # type: ignore

def safe_int_convert(value: Any) -> int:
    """Safely convert value to int with explicit typing."""
    if isinstance(value, pd.Series):
        return int(value.iloc[0]) if len(value) > 0 else 0  # type: ignore
    elif isinstance(value, (int, np.integer)):
        return int(value)
    elif isinstance(value, (float, np.floating)):
        return int(value)
    elif isinstance(value, str):
        return int(float(value))
    else:
        return int(value)  # type: ignore

def safe_float_convert(value: Any) -> float:
    """Safely convert value to float with explicit typing."""
    if isinstance(value, pd.Series):
        return float(value.iloc[0]) if len(value) > 0 else 0.0  # type: ignore
    elif isinstance(value, (float, np.floating)):
        return float(value)
    elif isinstance(value, (int, np.integer)):
        return float(value)
    elif isinstance(value, str):
        return float(value)
    else:
        return float(value)  # type: ignore

def safe_str_convert(value: Any) -> str:
    """Safely convert value to str with explicit typing."""
    if isinstance(value, pd.Series):
        return str(value.iloc[0]) if len(value) > 0 else ""  # type: ignore
    elif isinstance(value, str):
        return value
    else:
        return str(value)  # type: ignore

def convert_array_to_float(arr: Any) -> np.ndarray:
    """Convert any array-like to float numpy array with explicit typing."""
    if isinstance(arr, pd.Series):
        return np.array(arr.values, dtype=float)
    elif isinstance(arr, np.ndarray):
        return np.array(arr, dtype=float)
    else:
        return np.array(arr, dtype=float)  # type: ignore

def convert_array_to_str(arr: Any) -> np.ndarray:
    """Convert any array-like to string numpy array with explicit typing."""
    if isinstance(arr, pd.Series):
        return np.array(arr.values, dtype=str)
    elif isinstance(arr, np.ndarray):
        return np.array(arr, dtype=str)
    else:
        return np.array(arr, dtype=str)  # type: ignore
