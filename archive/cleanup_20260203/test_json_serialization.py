#!/usr/bin/env python
"""
Test JSON serialization with numpy arrays and special values.
Ensures our sanitize_for_json function handles edge cases.
"""

from __future__ import annotations

import json
import numpy as np
from pathlib import Path

# Test data with problematic types
test_data = {
    "agent": "SAC",
    "steps": 26277,
    "carbon_kg": float('-inf'),  # Could happen with certain metrics
    "co2_neto_kg": -3830891.6,
    "grid_import_kwh": 1635000.0,
    "numpy_array": np.array([1.0, 2.0, np.nan, np.inf, -np.inf]),
    "numpy_float": np.float64(123.456),
    "numpy_int": np.int64(789),
    "dict_nested": {
        "inner_array": np.array([1, 2, 3]),
        "special_value": np.nan,
    },
}


def sanitize_for_json(obj):
    """Convert problematic types to JSON-serializable values."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        arr = obj.astype(object)
        return [sanitize_for_json(v) for v in arr.tolist()]
    elif isinstance(obj, (np.floating, np.integer)):
        val = float(obj)
        if np.isnan(val):
            return "NaN"
        elif np.isinf(val):
            return "Infinity" if val > 0 else "-Infinity"
        return val
    elif isinstance(obj, (float, int)):
        if np.isnan(obj):
            return "NaN"
        elif np.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, str):
        return obj
    elif obj is None:
        return None
    else:
        return str(obj)


if __name__ == "__main__":
    print("[TEST] JSON Serialization with sanitize_for_json\n")

    # Test 1: Sanitize and serialize
    print("1️⃣  Testing sanitization...")
    sanitized = sanitize_for_json(test_data)
    print(f"   ✅ Sanitized successfully")

    # Test 2: JSON dump
    print("2️⃣  Testing JSON encoding...")
    try:
        json_str = json.dumps(sanitized, indent=2, ensure_ascii=False)
        print(f"   ✅ JSON encoded successfully ({len(json_str)} bytes)")
    except Exception as e:
        print(f"   ❌ JSON encoding failed: {e}")
        exit(1)

    # Test 3: Write to file
    print("3️⃣  Testing file write...")
    test_path = Path("test_result_SAC.json")
    try:
        test_path.write_text(json_str, encoding="utf-8")
        print(f"   ✅ File written successfully: {test_path}")
    except Exception as e:
        print(f"   ❌ File write failed: {e}")
        exit(1)

    # Test 4: Read and verify
    print("4️⃣  Testing file read...")
    try:
        read_data = json.loads(test_path.read_text(encoding="utf-8"))
        print(f"   ✅ File read and parsed successfully")
        print(f"\n📋 Sample data from file:")
        print(f"   Agent: {read_data.get('agent')}")
        print(f"   Steps: {read_data.get('steps')}")
        print(f"   CO2 neto: {read_data.get('co2_neto_kg')}")
        print(f"   Numpy array values: {read_data.get('numpy_array')}")
    except Exception as e:
        print(f"   ❌ File read failed: {e}")
        exit(1)

    # Cleanup
    test_path.unlink()

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - JSON serialization is robust!")
    print("="*60)
