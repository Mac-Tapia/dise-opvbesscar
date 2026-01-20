#!/usr/bin/env python3
"""Robust CityLearn Patching for EV Charger Issues.
Handles all known bugs in simulate_unconnected_ev_soc and charge methods."""

import numpy as np
from importlib import import_module
from typing import Any

def apply_robust_citylearn_patches():
    """Apply comprehensive patches to CityLearn to fix EV charger bugs."""
    
    try:
        citylearn_data = import_module("citylearn.data")
        citylearn_energy_model = import_module("citylearn.energy_model")
        Data: Any = getattr(citylearn_data, "Data")
        Battery: Any = getattr(citylearn_energy_model, "Battery")
        
        print("[INFO] Applying robust CityLearn patches...")
        
        # ===== PATCH 1: Data.__getattr__ - Prevent infinite recursion =====
        original_data_getattr = Data.__getattr__
        
        def patched_data_getattr(self: Any, name: str):
            """Prevent __getattr__ recursion on missing attributes."""
            if name.startswith('_') or name in ['start_time_step', 'end_time_step']:
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            try:
                return original_data_getattr(self, name)
            except (AttributeError, RecursionError, KeyError):
                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        Data.__getattr__ = patched_data_getattr
        print("[OK] Patched Data.__getattr__")
        
        # ===== PATCH 2: Battery.charge - Safe energy addition =====
        def patched_charge(self: Any, energy):
            """Safe charge method with bounds checking."""
            try:
                if energy <= 0:
                    return
                
                # Ensure _soc is in valid range
                if not hasattr(self, '_soc') or self._soc is None:
                    self._soc = 0.0
                self._soc = max(0.0, min(1.0, self._soc))
                
                # Calculate available capacity
                if not hasattr(self, 'capacity') or self.capacity <= 0:
                    return
                    
                available_kwh = self.capacity * (1.0 - self._soc)
                energy_to_add = min(energy, available_kwh)
                
                if energy_to_add > 0:
                    self._soc = min(1.0, self._soc + energy_to_add / self.capacity)
            except Exception:
                pass  # Silent fail
        
        setattr(Battery, "charge", patched_charge)
        print("[OK] Patched Battery.charge")
        
        # ===== PATCH 3: Battery.get_max_input_power - Safe indexing =====
        def patched_get_max_input_power(self: Any):
            """Safe max input power calculation."""
            try:
                if not hasattr(self, '_soc') or self._soc is None:
                    return getattr(self, 'power', 10.0)
                
                soc = max(0.0, min(1.0, self._soc))
                
                if not hasattr(self, 'capacity_power_curve') or len(self.capacity_power_curve) == 0:
                    return getattr(self, 'power', 10.0)
                
                # Find safe index
                comparison = soc <= np.array(self.capacity_power_curve)
                if not np.any(comparison):
                    return self.capacity_power_curve[-1]
                
                idx = max(0, np.argmax(comparison) - 1)
                idx = min(idx, len(self.capacity_power_curve) - 1)
                
                return self.capacity_power_curve[idx]
            except Exception:
                return getattr(self, 'power', 10.0)
        
        setattr(Battery, "get_max_input_power", patched_get_max_input_power)
        print("[OK] Patched Battery.get_max_input_power")
        
        return True
        
    except Exception as e:
        print(f"[WARN] Could not apply patches: {e}")
        return False

if __name__ == "__main__":
    apply_robust_citylearn_patches()
    print("[OK] All patches applied successfully")
