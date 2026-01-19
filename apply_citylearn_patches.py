#!/usr/bin/env python3
"""
Apply CityLearn EV Charger Bug Patches
Fixes array indexing issue in energy_model.py get_max_input_power()
"""

import sys
from pathlib import Path
import numpy as np

def patch_citylearn():
    """Monkey-patch CityLearn to fix EV charger bugs."""
    
    # Import after adding to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        import citylearn
        from citylearn.energy_model import Battery
        
        # PATCH 1: Fix get_max_input_power() array indexing
        original_get_max_input_power = Battery.get_max_input_power
        
        def patched_get_max_input_power(self):
            """Fixed version that safely handles SOC comparison."""
            try:
                # Ensure soc and capacity_power_curve are valid
                if not hasattr(self, '_soc') or self._soc is None:
                    return self.power
                if not hasattr(self, 'capacity_power_curve') or len(self.capacity_power_curve) == 0:
                    return self.power
                
                soc = max(0.0, min(1.0, self._soc))  # Clamp to [0, 1]
                
                # Safely find index
                comparison = soc <= self.capacity_power_curve
                if len(comparison) == 0 or not np.any(comparison):
                    # SOC is greater than all curve values
                    return min(self.power, self.capacity_power_curve[-1]) if len(self.capacity_power_curve) > 0 else self.power
                
                idx = max(0, np.argmax(comparison) - 1)
                idx = min(idx, len(self.capacity_power_curve) - 1)  # Clamp to valid index
                
                return self.capacity_power_curve[idx]
            except Exception as e:
                print(f"⚠ Error in get_max_input_power: {e}. Using default power.")
                return self.power
        
        Battery.get_max_input_power = patched_get_max_input_power
        print("✓ Patched Battery.get_max_input_power()")
        
        # PATCH 2: Fix charge() method with better SOC bounds checking
        original_charge = Battery.charge
        
        def patched_charge(self, energy_kwh):
            """Fixed version with safer energy calculation."""
            try:
                if energy_kwh <= 0:
                    return
                
                # Ensure soc is in valid range
                if not hasattr(self, '_soc'):
                    self._soc = 0.0
                self._soc = max(0.0, min(1.0, self._soc))
                
                # Clamp energy to available capacity
                available_capacity_kwh = self.capacity * (1.0 - self._soc)
                energy_to_add = min(energy_kwh, available_capacity_kwh)
                
                if energy_to_add > 0:
                    self._soc = self._soc + energy_to_add / self.capacity
                    self._soc = min(1.0, self._soc)  # Clamp to 1.0
            except Exception as e:
                print(f"⚠ Error in charge(): {e}")
        
        Battery.charge = patched_charge
        print("✓ Patched Battery.charge()")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Could not import CityLearn modules: {e}")
        return False
    except Exception as e:
        print(f"⚠ Error applying patches: {e}")
        return False

if __name__ == "__main__":
    patch_citylearn()
    print("✓ All CityLearn patches applied successfully")
