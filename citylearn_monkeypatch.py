#!/usr/bin/env python3
"""
Parche para CityLearn - Corrige infinite recursion en simulate_unconnected_ev_soc()
Debe importarse ANTES de que se cargue simulate
"""

import numpy as np

def apply_citylearn_patches():
    """Aplicar patches a CityLearn para evitar errores de acceso a atributos."""
    
    try:
        from citylearn.citylearn import CityLearnEnv
        
        original_simulate_unconnected = CityLearnEnv.simulate_unconnected_ev_soc
        
        def _patched_simulate_unconnected_ev_soc(self):
            """Parche para simulate_unconnected_ev_soc - evita infinite recursion."""
            try:
                t = self.time_step
                if t + 1 >= self.episode_tracker.episode_time_steps:
                    return
        
                for ev in self.electric_vehicles:
                    ev_id = ev.name
                    found_in_charger = False
        
                    for building in self.buildings:
                        for charger in building.electric_vehicle_chargers or []:
                            sim = charger.charger_simulation
                            try:
                                # Acceso directo a atributos privados para evitar __getattr__
                                ev_id_data = object.__getattribute__(sim, '_electric_vehicle_id')
                                ev_state_data = object.__getattribute__(sim, '_electric_vehicle_charger_state')
                                ev_arrival_data = object.__getattribute__(sim, '_electric_vehicle_estimated_soc_arrival')
                                
                                # Bounds checking
                                curr_id = ev_id_data[t] if t < len(ev_id_data) else ""
                                next_id = ev_id_data[t + 1] if t + 1 < len(ev_id_data) else ""
                                curr_state = ev_state_data[t] if t < len(ev_state_data) else np.nan
                                next_state = ev_state_data[t + 1] if t + 1 < len(ev_state_data) else np.nan
                            except (AttributeError, IndexError, TypeError):
                                continue
        
                            currently_connected = isinstance(curr_id, str) and curr_id == ev_id and curr_state == 1
                            if currently_connected:
                                found_in_charger = True
                                break
        
                            is_connecting = (
                                isinstance(next_id, str)
                                and next_id == ev_id
                                and next_state == 1
                                and curr_state != 1
                            )
                            is_incoming = isinstance(curr_id, str) and curr_id == ev_id and curr_state == 2
        
                            if is_connecting:
                                found_in_charger = True
                                if is_incoming:
                                    soc = ev_arrival_data[t] if t < len(ev_arrival_data) else np.nan
                                else:
                                    soc = ev_arrival_data[t + 1] if t + 1 < len(ev_arrival_data) else np.nan
        
                                if 0 <= soc <= 1:
                                    try:
                                        ev.battery.force_set_soc(soc)
                                    except Exception:
                                        pass
                                break
        
                        if found_in_charger:
                            break
        
                    if not found_in_charger:
                        # SOC drift para EVs no conectados
                        if t > 0:
                            try:
                                last_soc = ev.battery.soc[t - 1]
                                variability = np.clip(np.random.normal(1.0, 0.2), 0.6, 1.4)
                                new_soc = np.clip(last_soc * variability, 0.0, 1.0)
                                ev.battery.force_set_soc(new_soc)
                            except (IndexError, TypeError, AttributeError):
                                pass
            except Exception:
                pass  # Fail silently
        
        CityLearnEnv.simulate_unconnected_ev_soc = _patched_simulate_unconnected_ev_soc
        return True
        
    except Exception as e:
        return False

if __name__ == "__main__":
    if apply_citylearn_patches():
        print("[OK] CityLearn patches applied")
    else:
        print("[WARN] Could not apply CityLearn patches")
