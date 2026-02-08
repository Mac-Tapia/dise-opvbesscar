#!/usr/bin/env python3
"""Callback mejorado: motos/mototaxis + reducción CO2 directo/indirecto por iteración."""

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

class VehicleCO2LoggingCallback(BaseCallback):
    """
    Callback que muestra por iteración:
    - Motos/mototaxis cargando
    - Reducción CO2 DIRECTA (solar → EV en lugar de grid)
    - Reducción CO2 INDIRECTA (PV directo que evita grid import)
    - Total CO2 evitado
    """
    
    def __init__(self, env_ref=None, verbose=0, log_interval=1000):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.log_interval = log_interval
        
        # Tracking por episodio
        self.episode_motos_total = 0
        self.episode_mototaxis_total = 0
        self.episode_co2_direct = 0  # kg CO2 evitado directo
        self.episode_co2_indirect = 0  # kg CO2 evitado indirecto
        self.episode_co2_total = 0
        
        self.total_steps = 0
        
        # Factores Iquitos
        self.CO2_GRID_FACTOR = 0.4521  # kg CO2/kWh (grid térmico aislado)
        self.CO2_EV_FACTOR = 2.146     # kg CO2/kWh (conversión directa)
    
    def _on_step(self) -> bool:
        """Llamado después de cada step."""
        self.total_steps += 1
        
        # Extraer estado del environment
        if self.env_ref is None or not hasattr(self.env_ref, 'env'):
            return True
        
        env = self.env_ref
        
        # Obtener métricas del step actual
        try:
            # Variables de vehículos
            motos_charging = getattr(env, 'motos_charging_this_step', 0)
            mototaxis_charging = getattr(env, 'mototaxis_charging_this_step', 0)
            
            # Variables CO2
            # Reducción DIRECTA: CO2 que se evita por no generar EV charging desde grid
            grid_import_kwh = getattr(env, 'grid_import_kwh', 0)
            solar_to_ev = getattr(env, 'solar_to_ev_kwh', 0)  # Solar directo a EV
            
            # Reducción INDIRECTA: CO2 del grid que se evita por usar solar
            # = Solar directo × factor CO2 grid
            co2_direct_avoided = solar_to_ev * self.CO2_EV_FACTOR
            co2_indirect_avoided = solar_to_ev * self.CO2_GRID_FACTOR
            
            # Acumular
            self.episode_motos_total += motos_charging
            self.episode_mototaxis_total += mototaxis_charging
            self.episode_co2_direct += co2_direct_avoided
            self.episode_co2_indirect += co2_indirect_avoided
            self.episode_co2_total += (co2_direct_avoided + co2_indirect_avoided)
            
            # Log cada log_interval pasos
            if self.total_steps % self.log_interval == 0:
                episode_num = self.total_steps // 8760
                progreso = ((self.total_steps % 8760) / 8760) * 100
                
                print(f"  Step {self.total_steps:>7d} | "
                      f"Ep {episode_num:>2d} ({progreso:>5.1f}%) | "
                      f"Motos: {motos_charging:>3d}/112 | "
                      f"Mototaxis: {mototaxis_charging:>3d}/16 | "
                      f"CO2_dir: {co2_direct_avoided:>8,.0f}kg | "
                      f"CO2_ind: {co2_indirect_avoided:>8,.0f}kg")
        
        except Exception as e:
            # Continuar sin errores
            pass
        
        return True
    
    def _on_episode_end(self) -> None:
        """Llamado al final de cada episodio."""
        episode_num = self.total_steps // 8760
        
        # Calcular promedios
        motos_por_hora = self.episode_motos_total / 8760
        mototaxis_por_hora = self.episode_mototaxis_total / 8760
        motos_por_dia = motos_por_hora * 24
        mototaxis_por_dia = mototaxis_por_hora * 24
        
        co2_direct_por_hora = self.episode_co2_direct / 8760
        co2_indirect_por_hora = self.episode_co2_indirect / 8760
        co2_total_por_hora = self.episode_co2_total / 8760
        
        co2_direct_por_dia = co2_direct_por_hora * 24
        co2_indirect_por_dia = co2_indirect_por_hora * 24
        co2_total_por_dia = co2_total_por_hora * 24
        
        print(f"\n  {'='*80}")
        print(f"  EPISODIO {episode_num + 1} COMPLETADO")
        print(f"  {'='*80}")
        
        print(f"\n  📊 VEHÍCULOS CARGADOS:")
        print(f"    Motos:")
        print(f"      • Total episodio: {self.episode_motos_total:>12,.0f}")
        print(f"      • Promedio/hora:  {motos_por_hora:>12.1f}")
        print(f"      • Promedio/día:   {motos_por_dia:>12.1f}")
        print(f"    Mototaxis:")
        print(f"      • Total episodio: {self.episode_mototaxis_total:>12,.0f}")
        print(f"      • Promedio/hora:  {mototaxis_por_hora:>12.1f}")
        print(f"      • Promedio/día:   {mototaxis_por_dia:>12.1f}")
        
        print(f"\n  🌍 REDUCCIÓN CO2 DIRECTA (demanda EV):")
        print(f"      • Total episodio: {self.episode_co2_direct:>12,.1f} kg")
        print(f"      • Promedio/hora:  {co2_direct_por_hora:>12.1f} kg/h")
        print(f"      • Promedio/día:   {co2_direct_por_dia:>12.1f} kg/día")
        
        print(f"\n  ☀️  REDUCCIÓN CO2 INDIRECTA (solar → grid):")
        print(f"      • Total episodio: {self.episode_co2_indirect:>12,.1f} kg")
        print(f"      • Promedio/hora:  {co2_indirect_por_hora:>12.1f} kg/h")
        print(f"      • Promedio/día:   {co2_indirect_por_dia:>12.1f} kg/día")
        
        print(f"\n  ✅ CO2 TOTAL EVITADO:")
        print(f"      • Total episodio: {self.episode_co2_total:>12,.1f} kg")
        print(f"      • Promedio/hora:  {co2_total_por_hora:>12.1f} kg/h")
        print(f"      • Promedio/día:   {co2_total_por_dia:>12.1f} kg/día")
        
        print(f"  {'='*80}\n")
        
        # Reset para próximo episodio
        self.episode_motos_total = 0
        self.episode_mototaxis_total = 0
        self.episode_co2_direct = 0
        self.episode_co2_indirect = 0
        self.episode_co2_total = 0


# Ejemplo de uso:
"""
from stable_baselines3.common.callbacks import CallbackList

# Crear callbacks
checkpoint_callback = CheckpointCallback(...)
vehicle_co2_callback = VehicleCO2LoggingCallback(env_ref=env, log_interval=1000)

# Combinar
callbacks = CallbackList([checkpoint_callback, vehicle_co2_callback])

# Usar en entrenamiento
model.learn(
    total_timesteps=TOTAL_TIMESTEPS,
    callback=callbacks,
    progress_bar=True
)
"""

if __name__ == "__main__":
    print("\n" + "="*80)
    print("📊 CALLBACK: VEHÍCULOS + CO2 DIRECTO/INDIRECTO")
    print("="*80 + "\n")
    
    print("✅ Clase VehicleCO2LoggingCallback creada\n")
    
    print("📋 VARIABLES RASTREADAS POR ITERACIÓN:")
    print("  • Motos cargando (0-112)")
    print("  • Mototaxis cargando (0-16)")
    print("  • CO2 reducción DIRECTA (kg/h)")
    print("  • CO2 reducción INDIRECTA (kg/h)\n")
    
    print("📊 VARIABLES REPORTADAS POR EPISODIO:")
    print("  • Total motos cargadas")
    print("  • Promedio motos por hora/día")
    print("  • Total mototaxis cargadas")
    print("  • Promedio mototaxis por hora/día")
    print("  • CO2 directo: total, por hora, por día")
    print("  • CO2 indirecto: total, por hora, por día")
    print("  • CO2 total evitado: total, por hora, por día\n")
    
    print("✅ Listo para integrar en train_ppo/a2c/sac_multiobjetivo.py\n")
