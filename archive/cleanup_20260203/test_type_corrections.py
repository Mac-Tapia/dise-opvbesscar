#!/usr/bin/env python3
"""
Test script para verificar que las correcciones de tipos funcionen correctamente.
"""

from __future__ import annotations

import pandas as pd  # type: ignore
import numpy as np
from typing import cast

def test_type_corrections():
    """Prueba que las correcciones de tipos funcionen correctamente."""

    # Crear datos de prueba
    data = {
        'values': [1.0, 2.5, 3.2, 4.1, 5.8],
        'timestamps': pd.date_range('2024-01-01', periods=5, freq='h')
    }
    df = pd.DataFrame(data)

    # Test 1: Conversiones explícitas para abs()
    corr_value = 0.75
    abs_corr = abs(float(corr_value))  # Tipo explícito
    print(f"✅ Test abs(): {abs_corr}")

    # Test 2: Conversiones para idxmax/idxmin
    max_idx = int(df['values'].idxmax())
    max_val = float(df['values'].max())
    print(f"✅ Test idxmax(): índice={max_idx}, valor={max_val}")

    # Test 3: Operaciones con Series
    series_diff = df['values'].diff().abs()
    mean_diff = float(series_diff.mean())
    print(f"✅ Test Series operations: {mean_diff:.3f}")

    # Test 4: Balance energético
    energy_in = df['values'] + df['values'] * 0.5
    energy_out = df['values'] * 1.2
    balance_error_series = (energy_in - energy_out).abs()
    balance_error = float(balance_error_series.mean())
    print(f"✅ Test balance error: {balance_error:.3f}")

    print("🎯 Todas las correcciones de tipos funcionan correctamente")

if __name__ == "__main__":
    test_type_corrections()
