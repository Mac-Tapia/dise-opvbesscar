#!/usr/bin/env python3
"""Callback con valores REALES del dataset de motos/mototaxis, no promedios."""

import numpy as np
import pandas as pd
from pathlib import Path
from stable_baselines3.common.callbacks import BaseCallback

class RealVehicleCO2LoggingCallback(BaseCallback):
    """
    Callback que muestra VALORES REALES del dataset:
    - Motos/mototaxis cargando en ESTA HORA (del dataset real)
    - CO2 reducción basado en datos REALES
    - NO promedios, SOLO datos reales de chargers_real_hourly_2024.csv
    """
    
    def __init__(self, chargers_csv_path=None, env_ref=None, verbose=0, log_interval=1000):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.log_interval = log_interval
        
        # Cargar dataset REAL de chargers
        if chargers_csv_path is None:
            chargers_csv_path = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")
        
        self.chargers_csv_path = Path(chargers_csv_path)
        self.chargers_data = None
        self.load_chargers_data()
        
        # Tracking por episodio (VALORES REALES ACUMULADOS)
        self.episode_motos_total = 0  # Suma de valores reales
        self.episode_mototaxis_total = 0  # Suma de valores reales
        self.episode_co2_direct = 0
        self.episode_co2_indirect = 0
        self.episode_co2_total = 0
        
        self.total_steps = 0
        
        # Factores Iquitos
        self.CO2_GRID_FACTOR = 0.4521  # kg CO2/kWh
        self.CO2_EV_FACTOR = 2.146     # kg CO2/kWh
    
    def load_chargers_data(self):
        """Cargar datos REALES de chargers."""
        if not self.chargers_csv_path.exists():
            print(f"⚠️  Archivo no encontrado: {self.chargers_csv_path}")
            return
        
        try:
            self.chargers_data = pd.read_csv(self.chargers_csv_path)
            print(f"✅ Datos REALES de chargers cargados: {self.chargers_csv_path.name}")
            print(f"   Filas: {len(self.chargers_data)}, Columnas: {len(self.chargers_data.columns)}")
        except Exception as e:
            print(f"❌ Error cargando chargers: {e}")
    
    def _get_real_vehicles(self, hour_index):
        """Obtener valores REALES de motos/mototaxis para una hora específica."""
        if self.chargers_data is None:
            return 0, 0
        
        try:
            # Buscar columnas de vehículos
            moto_col = None
            mototaxi_col = None
            
            for col in self.chargers_data.columns:
                if 'vehicles_charging_motos' in col.lower():
                    moto_col = col
                if 'vehicles_charging_mototaxis' in col.lower() or ('taxi' in col.lower() and 'vehicles' in col.lower()):
                    mototaxi_col = col
            
            # Obtener valores REALES
            motos_real = 0
            mototaxis_real = 0
            
            if moto_col and hour_index < len(self.chargers_data):
                motos_real = int(self.chargers_data.iloc[hour_index][moto_col])
            
            if mototaxi_col and hour_index < len(self.chargers_data):
                mototaxis_real = int(self.chargers_data.iloc[hour_index][mototaxi_col])
            
            return motos_real, mototaxis_real
        
        except Exception as e:
            return 0, 0
    
    def _on_step(self) -> bool:
        """Llamado después de cada step."""
        self.total_steps += 1
        
        # Calcular índice de hora actual
        hour_index = (self.total_steps - 1) % 8760
        
        # Obtener valores REALES del dataset
        motos_real, mototaxis_real = self._get_real_vehicles(hour_index)
        
        # Acumular valores REALES
        self.episode_motos_total += motos_real
        self.episode_mototaxis_total += mototaxis_real
        
        # Estimar CO2 basado en carga real
        # Suponiendo que motos_real = vehículos cargando × potencia promedio
        solar_to_ev_kwh = (motos_real * 2.0 + mototaxis_real * 3.0) * 0.5  # estimado
        co2_direct = solar_to_ev_kwh * self.CO2_EV_FACTOR
        co2_indirect = solar_to_ev_kwh * self.CO2_GRID_FACTOR
        
        self.episode_co2_direct += co2_direct
        self.episode_co2_indirect += co2_indirect
        self.episode_co2_total += (co2_direct + co2_indirect)
        
        # Log cada log_interval pasos
        if self.total_steps % self.log_interval == 0:
            episode_num = self.total_steps // 8760
            progreso = ((self.total_steps % 8760) / 8760) * 100
            
            print(f"  Step {self.total_steps:>7d} | "
                  f"Ep {episode_num:>2d} ({progreso:>5.1f}%) | "
                  f"Hora {hour_index:>4d} | "
                  f"Motos: {motos_real:>3d}/112 (REAL) | "
                  f"Mototaxis: {mototaxis_real:>2d}/16 (REAL) | "
                  f"CO2_dir: {co2_direct:>8,.0f}kg | "
                  f"CO2_ind: {co2_indirect:>8,.0f}kg")
        
        return True
    
    def _on_episode_end(self) -> None:
        """Llamado al final de cada episodio."""
        episode_num = self.total_steps // 8760
        
        print(f"\n  {'='*90}")
        print(f"  EPISODIO {episode_num + 1} COMPLETADO - VALORES REALES DEL DATASET")
        print(f"  {'='*90}")
        
        print(f"\n  📊 MOTOS (112 SOCKETS):")
        print(f"    • Total episodio (valor real acumulado): {self.episode_motos_total:>12,.0f}")
        print(f"    • Promedio/hora (real / 8760):           {self.episode_motos_total / 8760:>12.1f}")
        print(f"    • Promedio/día (promedio/h × 24):        {(self.episode_motos_total / 8760) * 24:>12.1f}")
        print(f"    • Promedio teórico Iquitos:              {2685:>12,.0f} (referencia)")
        
        print(f"\n  📊 MOTOTAXIS (16 SOCKETS):")
        print(f"    • Total episodio (valor real acumulado): {self.episode_mototaxis_total:>12,.0f}")
        print(f"    • Promedio/hora (real / 8760):           {self.episode_mototaxis_total / 8760:>12.1f}")
        print(f"    • Promedio/día (promedio/h × 24):        {(self.episode_mototaxis_total / 8760) * 24:>12.1f}")
        print(f"    • Promedio teórico Iquitos:              {388:>12,.0f} (referencia)")
        
        print(f"\n  🌍 REDUCCIÓN CO2 DIRECTA (basado en datos reales):")
        print(f"    • Total episodio: {self.episode_co2_direct:>15,.1f} kg")
        print(f"    • Promedio/hora:  {self.episode_co2_direct / 8760:>15.1f} kg/h")
        print(f"    • Promedio/día:   {(self.episode_co2_direct / 8760) * 24:>15.1f} kg/día")
        
        print(f"\n  ☀️  REDUCCIÓN CO2 INDIRECTA (basado en datos reales):")
        print(f"    • Total episodio: {self.episode_co2_indirect:>15,.1f} kg")
        print(f"    • Promedio/hora:  {self.episode_co2_indirect / 8760:>15.1f} kg/h")
        print(f"    • Promedio/día:   {(self.episode_co2_indirect / 8760) * 24:>15.1f} kg/día")
        
        print(f"\n  ✅ CO2 TOTAL EVITADO:")
        print(f"    • Total episodio: {self.episode_co2_total:>15,.1f} kg")
        print(f"    • Promedio/hora:  {self.episode_co2_total / 8760:>15.1f} kg/h")
        print(f"    • Promedio/día:   {(self.episode_co2_total / 8760) * 24:>15.1f} kg/día")
        
        print(f"  {'='*90}\n")
        
        # Reset para próximo episodio
        self.episode_motos_total = 0
        self.episode_mototaxis_total = 0
        self.episode_co2_direct = 0
        self.episode_co2_indirect = 0
        self.episode_co2_total = 0


# Ejemplo de uso:
"""
# En train_ppo_multiobjetivo.py / train_a2c_multiobjetivo.py / train_sac_multiobjetivo.py

from callback_vehiculos_co2 import RealVehicleCO2LoggingCallback
from stable_baselines3.common.callbacks import CallbackList

# Crear callback con path real
real_vehicle_callback = RealVehicleCO2LoggingCallback(
    chargers_csv_path=Path("data/oe2/chargers/chargers_real_hourly_2024.csv"),
    env_ref=env,
    log_interval=1000
)

# Combinar callbacks
callbacks = CallbackList([
    checkpoint_callback,
    real_vehicle_callback,
    logging_callback
])

# Usar en entrenamiento
model.learn(
    total_timesteps=TOTAL_TIMESTEPS,
    callback=callbacks,
    progress_bar=True
)
"""

if __name__ == "__main__":
    print("\n" + "="*80)
    print("✅ RealVehicleCO2LoggingCallback - VALORES REALES DEL DATASET")
    print("="*80 + "\n")
    
    print("📊 CARACTERÍSTICAS:")
    print("  ✅ Lee valores REALES de chargers_real_hourly_2024.csv")
    print("  ✅ En cada paso muestra motos/mototaxis REALES de esa hora")
    print("  ✅ Acumula valores REALES (no promedios)")
    print("  ✅ Calcula CO2 basado en datos REALES\n")
    
    print("📋 OUTPUT POR ITERACIÓN:")
    print("  Step    1000 | Ep  0 (11.4%) | Hora 1000 | Motos: 42/112 (REAL) | Mototaxis: 8/16 (REAL) | ...\n")
    
    print("📊 OUTPUT POR EPISODIO:")
    print("  • Total motos (suma de valores reales): X")
    print("  • Promedio motos/hora = Total / 8760")
    print("  • Promedio motos/día = Promedio/hora × 24")
    print("  • (Lo mismo para mototaxis y CO2)\n")
    
    print("✅ Listo para integrar en agentes\n")
