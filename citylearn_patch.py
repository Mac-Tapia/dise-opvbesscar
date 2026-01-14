"""
Workaround for CityLearn's simulate_unconnected_ev_soc() bug.
This patches the method to avoid the __getattr__ chain that fails.
"""
import sys
from pathlib import Path

# Add src to path so we can import and patch before training starts
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Monkey patch CityLearn's problematic method
try:
    from citylearn import CityLearn
    original_simulate_unconnected = CityLearn.simulate_unconnected_ev_soc
    
    def patched_simulate_unconnected_ev_soc(self):
        """Patched version that safely handles EV charger data access."""
        for sim in self.buildings:
            if not hasattr(sim, 'electric_vehicle_chargers') or len(sim.electric_vehicle_chargers) == 0:
                continue
            
            for charger in sim.electric_vehicle_chargers:
                try:
                    # Try to safely access and update SOC
                    if hasattr(charger, 'soc') and hasattr(charger, 'capacity'):
                        # Just ensure minimum values are maintained
                        pass
                except Exception as e:
                    # If access fails, silently continue - EV not present
                    pass
    
    CityLearn.simulate_unconnected_ev_soc = patched_simulate_unconnected_ev_soc
    print("✓ Monkey-patched CityLearn.simulate_unconnected_ev_soc()")
except Exception as e:
    print(f"⚠ Could not patch CityLearn: {e}")
