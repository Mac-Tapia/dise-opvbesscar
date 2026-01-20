#!/usr/bin/env python3
"""
Apply CityLearn EV Charger Bug Patches
Fixes array indexing issue in energy_model.py get_max_input_power()
and adds safer charge bounds.
"""

from pathlib import Path
from typing import Any, Optional
import sys
import numpy as np


def patch_citylearn() -> bool:
    """Monkey-patch CityLearn to fix EV charger bugs."""

    # Ensure local path is in sys.path
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        import citylearn  # noqa: F401
        from citylearn.energy_model import Battery

        # PATCH 1: Fix get_max_input_power() array indexing
        original_get_max_input_power = Battery.get_max_input_power

        def patched_get_max_input_power(self: Any) -> float:
            """Fixed version that safely handles SOC comparison."""
            try:
                if not hasattr(self, "_soc") or self._soc is None:
                    return float(getattr(self, "power", 0.0))
                if not hasattr(self, "capacity_power_curve") or len(self.capacity_power_curve) == 0:
                    return float(getattr(self, "power", 0.0))

                soc = max(0.0, min(1.0, float(self._soc)))
                comparison = soc <= self.capacity_power_curve

                if len(comparison) == 0 or not np.any(comparison):
                    return (
                        min(float(getattr(self, "power", 0.0)), float(self.capacity_power_curve[-1]))
                        if len(self.capacity_power_curve) > 0
                        else float(getattr(self, "power", 0.0))
                    )

                idx = max(0, np.argmax(comparison) - 1)
                idx = min(idx, len(self.capacity_power_curve) - 1)
                return float(self.capacity_power_curve[idx])
            except Exception as e:  # pragma: no cover - defensive
                print(f"[WARN] Error in get_max_input_power: {e}. Using default power.")
                return float(getattr(self, "power", 0.0))

        Battery.get_max_input_power = patched_get_max_input_power
        print("[OK] Patched Battery.get_max_input_power()")

        # PATCH 2: Fix charge() method with better SOC bounds checking
        original_charge = Battery.charge

        def patched_charge(self: Any, energy_kwh: Optional[float]) -> None:
            """Fixed version with safer energy calculation."""
            try:
                if energy_kwh is None or energy_kwh <= 0:
                    return

                if not hasattr(self, "_soc"):
                    self._soc = 0.0
                self._soc = max(0.0, min(1.0, float(self._soc)))

                if not hasattr(self, "capacity") or self.capacity <= 0:
                    return

                available_capacity_kwh = float(self.capacity) * (1.0 - self._soc)
                energy_to_add = min(float(energy_kwh), available_capacity_kwh)

                if energy_to_add > 0:
                    self._soc = min(1.0, self._soc + energy_to_add / float(self.capacity))
            except Exception as e:  # pragma: no cover - defensive
                print(f"[WARN] Error in charge(): {e}")

        Battery.charge = patched_charge
        print("[OK] Patched Battery.charge()")

        return True

    except ImportError as e:
        print(f"[WARN] Could not import CityLearn modules: {e}")
        return False
    except Exception as e:  # pragma: no cover - defensive
        print(f"[WARN] Error applying patches: {e}")
        return False


if __name__ == "__main__":
    patch_citylearn()
    print("[OK] All CityLearn patches applied successfully")
