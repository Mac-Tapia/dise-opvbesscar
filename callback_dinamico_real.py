#!/usr/bin/env python3
"""
Callback DINÁMICO: Lee valores REALES hora por hora, calcula promedios en tiempo real.
Unidades IGUALES para motos y mototaxis.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from stable_baselines3.common.callbacks import BaseCallback

class DynamicRealVehicleCO2LoggingCallback(BaseCallback):
    """
    Callback DINÁMICO que:
    - Lee valores REALES del dataset hora por hora
    - Acumula dinámicamente durante el episodio
    - Calcula promedios REALES al final
    - Unidades CONSISTENTES para motos/mototaxis
    - CO2 calculado dinámicamente basado en carga real
    """
    
    def __init__(self, chargers_csv_path=None, env_ref=None, verbose=0, log_interval=1000):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.log_interval = log_interval
        
        # Cargar dataset REAL
        if chargers_csv_path is None:
            chargers_csv_path = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")
        
        self.chargers_csv_path = Path(chargers_csv_path)
        self.chargers_df = None
        self._load_chargers_data()
        
        # Tracking DINÁMICO por episodio
        self.episode_motos_acumulado = 0      # Suma REAL de todas las horas
        self.episode_mototaxis_acumulado = 0  # Suma REAL de todas las horas
        self.episode_co2_direct_acumulado = 0
        self.episode_co2_indirect_acumulado = 0
        
        self.episode_step_count = 0  # Contador de pasos en episodio actual
        self.total_steps = 0
        
        # Factores
        self.CO2_GRID_FACTOR = 0.4521      # kg CO2/kWh (grid Iquitos)
        self.CO2_EV_FACTOR = 2.146         # kg CO2/kWh (demanda EV)
        
        # Potencia típica
        self.MOTO_POWER = 2.0              # kW por moto
        self.MOTOTAXI_POWER = 3.0          # kW por mototaxi
    
    def _load_chargers_data(self):
        """Cargar dataset REAL."""
        if not self.chargers_csv_path.exists():
            print(f"⚠️  Archivo no encontrado: {self.chargers_csv_path}")
            return False
        
        try:
            self.chargers_df = pd.read_csv(self.chargers_csv_path)
            print(f"✅ Dataset REAL cargado: {self.chargers_csv_path.name}")
            print(f"   {len(self.chargers_df)} filas × {len(self.chargers_df.columns)} columnas")
            return True
        except Exception as e:
            print(f"❌ Error cargando dataset: {e}")
            return False
    
    def _get_real_vehicles_this_hour(self, hour_index):
        """
        Obtener valores REALES de motos/mototaxis para ESTA HORA del dataset.
        Returns: (motos_real, mototaxis_real)
        """
        if self.chargers_df is None or hour_index >= len(self.chargers_df):
            return 0, 0
        
        try:
            row = self.chargers_df.iloc[hour_index]
            
            # Buscar columnas correctas
            motos_real = 0
            mototaxis_real = 0
            
            for col in self.chargers_df.columns:
                col_lower = col.lower()
                
                if 'vehicles_charging_motos' in col_lower:
                    motos_real = int(row[col])
                
                if 'vehicles_charging_mototaxis' in col_lower:
                    mototaxis_real = int(row[col])
            
            return motos_real, mototaxis_real
        
        except Exception as e:
            return 0, 0
    
    def _on_step(self) -> bool:
        """Llamado después de cada step."""
        self.total_steps += 1
        self.episode_step_count += 1
        
        # Índice de hora actual (0-8759 en cada episodio)
        hour_index = (self.episode_step_count - 1) % 8760
        
        # Obtener valores REALES DINÁMICOS
        motos_real, mototaxis_real = self._get_real_vehicles_this_hour(hour_index)
        
        # Acumular DINÁMICAMENTE
        self.episode_motos_acumulado += motos_real
        self.episode_mototaxis_acumulado += mototaxis_real
        
        # Calcular CO2 DINÁMICO basado en carga REAL de ESTA HORA
        # Potencia = motos × 2kW + mototaxis × 3kW
        potencia_carga_kw = (motos_real * self.MOTO_POWER) + (mototaxis_real * self.MOTOTAXI_POWER)
        
        # CO2 DIRECTO = energía que evita combustión
        co2_direct_esta_hora = potencia_carga_kw * self.CO2_EV_FACTOR
        
        # CO2 INDIRECTO = energía que evita import del grid
        co2_indirect_esta_hora = potencia_carga_kw * self.CO2_GRID_FACTOR
        
        self.episode_co2_direct_acumulado += co2_direct_esta_hora
        self.episode_co2_indirect_acumulado += co2_indirect_esta_hora
        
        # LOG DINÁMICO cada log_interval pasos
        if self.total_steps % self.log_interval == 0:
            episode_num = (self.total_steps - 1) // 8760
            progreso_episodio = ((self.episode_step_count - 1) % 8760) / 8760 * 100
            
            # Calcular promedios DINÁMICOS hasta ahora
            promedio_motos_hasta_ahora = self.episode_motos_acumulado / self.episode_step_count if self.episode_step_count > 0 else 0
            promedio_mototaxis_hasta_ahora = self.episode_mototaxis_acumulado / self.episode_step_count if self.episode_step_count > 0 else 0
            
            print(f"  Step {self.total_steps:>7d} | "
                  f"Ep {episode_num:>2d} ({progreso_episodio:>5.1f}%) | "
                  f"Hora {hour_index:>4d} | "
                  f"Motos: {motos_real:>3d}/112 | "
                  f"Mototaxis: {mototaxis_real:>2d}/16 | "
                  f"CO2_dir: {co2_direct_esta_hora:>8.0f}kg | "
                  f"CO2_ind: {co2_indirect_esta_hora:>8.0f}kg")
        
        return True
    
    def _on_episode_end(self) -> None:
        """Llamado al final de cada episodio - calcula valores REALES FINALES."""
        episode_num = (self.total_steps - 1) // 8760
        
        # Calcular PROMEDIOS REALES basándose en valor acumulado
        promedio_motos_hora = self.episode_motos_acumulado / 8760
        promedio_mototaxis_hora = self.episode_mototaxis_acumulado / 8760
        
        promedio_motos_dia = promedio_motos_hora * 24
        promedio_mototaxis_dia = promedio_mototaxis_hora * 24
        
        # CO2 PROMEDIOS
        promedio_co2_direct_hora = self.episode_co2_direct_acumulado / 8760
        promedio_co2_direct_dia = promedio_co2_direct_hora * 24
        
        promedio_co2_indirect_hora = self.episode_co2_indirect_acumulado / 8760
        promedio_co2_indirect_dia = promedio_co2_indirect_hora * 24
        
        promedio_co2_total_hora = promedio_co2_direct_hora + promedio_co2_indirect_hora
        promedio_co2_total_dia = promedio_co2_total_hora * 24
        
        print(f"\n  {'='*100}")
        print(f"  EPISODIO {episode_num + 1} COMPLETADO - VALORES DINÁMICOS REALES DEL DATASET")
        print(f"  {'='*100}")
        
        print(f"\n  📊 MOTOS (112 SOCKETS) - VALORES REALES DINÁMICOS:")
        print(f"    • Total acumulado:      {self.episode_motos_acumulado:>12,.0f} motos-cargando")
        print(f"    • Promedio/hora:        {promedio_motos_hora:>12.1f} motos/hora")
        print(f"    • Promedio/día:         {promedio_motos_dia:>12.1f} motos/día")
        
        print(f"\n  📊 MOTOTAXIS (16 SOCKETS) - VALORES REALES DINÁMICOS:")
        print(f"    • Total acumulado:      {self.episode_mototaxis_acumulado:>12,.0f} mototaxis-cargando")
        print(f"    • Promedio/hora:        {promedio_mototaxis_hora:>12.1f} mototaxis/hora")
        print(f"    • Promedio/día:         {promedio_mototaxis_dia:>12.1f} mototaxis/día")
        
        print(f"\n  🌍 REDUCCIÓN CO2 DIRECTA (valores dinámicos reales):")
        print(f"    • Total acumulado:      {self.episode_co2_direct_acumulado:>12,.1f} kg")
        print(f"    • Promedio/hora:        {promedio_co2_direct_hora:>12.1f} kg/hora")
        print(f"    • Promedio/día:         {promedio_co2_direct_dia:>12.1f} kg/día")
        
        print(f"\n  ☀️  REDUCCIÓN CO2 INDIRECTA (valores dinámicos reales):")
        print(f"    • Total acumulado:      {self.episode_co2_indirect_acumulado:>12,.1f} kg")
        print(f"    • Promedio/hora:        {promedio_co2_indirect_hora:>12.1f} kg/hora")
        print(f"    • Promedio/día:         {promedio_co2_indirect_dia:>12.1f} kg/día")
        
        print(f"\n  ✅ CO2 TOTAL EVITADO (dinámico):")
        print(f"    • Total acumulado:      {self.episode_co2_direct_acumulado + self.episode_co2_indirect_acumulado:>12,.1f} kg")
        print(f"    • Promedio/hora:        {promedio_co2_total_hora:>12.1f} kg/hora")
        print(f"    • Promedio/día:         {promedio_co2_total_dia:>12.1f} kg/día")
        
        print(f"  {'='*100}\n")
        
        # RESET para próximo episodio
        self.episode_motos_acumulado = 0
        self.episode_mototaxis_acumulado = 0
        self.episode_co2_direct_acumulado = 0
        self.episode_co2_indirect_acumulado = 0
        self.episode_step_count = 0


if __name__ == "__main__":
    print("\n" + "="*80)
    print("✅ DynamicRealVehicleCO2LoggingCallback - VALORES DINÁMICOS")
    print("="*80 + "\n")
    
    print("📊 CARACTERÍSTICAS:")
    print("  ✅ Lee valores REALES hora por hora del dataset")
    print("  ✅ Acumula valores DINÁMICAMENTE durante el episodio")
    print("  ✅ Calcula PROMEDIOS basándose en valor acumulado real / 8760")
    print("  ✅ CO2 calculado dinámicamente (no fijo)")
    print("  ✅ Unidades IGUALES para motos y mototaxis\n")
    
    print("📋 UNIDADES UTILIZADAS:")
    print("  • Motos: motos/hora, motos/día")
    print("  • Mototaxis: mototaxis/hora, mototaxis/día")
    print("  • CO2: kg/hora, kg/día\n")
    
    print("🔄 FLUJO DINÁMICO:")
    print("  1. Cada step: Lee valor real de dataset para esa hora")
    print("  2. Cada step: Acumula valor real")
    print("  3. Al final: Promedio = acumulado / 8760")
    print("  4. CO2 basado en potencia real (motos × 2kW + mototaxis × 3kW)\n")
