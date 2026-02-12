# -*- coding: utf-8 -*-
"""
SIMULADOR BESS ANUAL - Datos reales 2024 (8,760 horas)
Simulación horaria completa con datos reales para 365 días
Iquitos, Perú - OE2
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

@dataclass(frozen=True)
class BESSSpecs:
    """Especificaciones BESS confirmadas."""
    capacity_kwh: float = 3022.0
    power_kw: float = 350.0
    dod_max: float = 0.90
    efficiency_round_trip: float = 0.92
    soc_min_percent: float = 10.0
    soc_max_percent: float = 100.0
    
    @property
    def usable_capacity_kwh(self) -> float:
        return self.capacity_kwh * self.dod_max
    
    @property
    def reserve_capacity_kwh(self) -> float:
        return self.capacity_kwh * (1.0 - self.dod_max)


def load_annual_profiles() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga perfiles anuales reales (8,760 horas cada uno)."""
    
    print("📂 Cargando datos anuales reales...")
    
    # 1. SOLAR: pv_generation_hourly_citylearn_v2.csv
    try:
        solar_df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
        print(f"   ✓ Solar cargada: {len(solar_df)} filas")
        if len(solar_df) != 8760:
            print(f"   ⚠️  Advertencia: Solar tiene {len(solar_df)} filas (esperadas 8,760)")
    except FileNotFoundError as e:
        print(f"   ✗ Error solar: {e}")
        raise
    
    # 2. MALL: demandamallhorakwh.csv (delimitador: ;)
    try:
        mall_df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';', decimal=',', encoding='utf-8')
        # Si falla el parsing, intentar interpretar manualmente
        if mall_df.shape[1] == 1:
            # Columna única con formato "fecha;kwh"
            col = mall_df.columns[0]
            parts = mall_df[col].str.split(';', expand=True)
            if parts.shape[1] == 2:
                mall_df = pd.DataFrame({
                    'timestamp': parts[0],
                    'demand_kwh': pd.to_numeric(parts[1], errors='coerce')
                })
        print(f"   ✓ Mall cargada: {len(mall_df)} filas")
        if len(mall_df) > 8760:
            mall_df = mall_df.iloc[:8760]
            print(f"   ℹ️  Truncada a 8,760 filas")
    except FileNotFoundError as e:
        print(f"   ✗ Error mall: {e}")
        raise
    
    # 3. EV: chargers_real_hourly_2024.csv (extraer demanda)
    try:
        ev_df = pd.read_csv('data/oe2/chargers/chargers_real_hourly_2024.csv')
        print(f"   ✓ EV cargada: {len(ev_df)} filas")
        if len(ev_df) != 8760:
            print(f"   ⚠️  Advertencia: EV tiene {len(ev_df)} filas (esperadas 8,760)")
    except FileNotFoundError as e:
        print(f"   ✗ Error EV: {e}")
        raise
    
    return solar_df, mall_df, ev_df


def extract_ev_demand(ev_df: pd.DataFrame) -> np.ndarray:
    """
    Extrae demanda EV desde el dataset chargers_ev_ano_2024_v3.csv (v5.2).
    
    NOTA IMPORTANTE (12-Feb-2026) - ACTUALIZADO v5.2:
    El archivo fuente (src/dimensionamiento/oe2/disenocargadoresev/chargers.py)
    ahora genera 38 tomas (19 cargadores × 2) @ 7.4 kW cada una:
    
    Cálculo v5.2:
    - 30 tomas motos: 1.0 cargas/hora × 4.6 kWh = ~138 kWh/h punta
    - 8 tomas mototaxis: 0.67 cargas/hora × 7.4 kWh = ~40 kWh/h punta
    - TOTAL TEÓRICO: ~178 kWh/h en hora punta (16-21h)
    - DIARIO: 1,529.9 kWh/día (270 motos × 4.6 + 39 mototaxis × 7.4)
    
    Si la columna existe, úsala directamente.
    Si no existe (dataset antiguo), calcular desde charging_power_kw.
    """
    
    # Intentar usar columna nueva
    if 'ev_demand_kwh' in ev_df.columns:
        return ev_df['ev_demand_kwh'].values
    
    # Fallback para datasets antiguos
    demanda_fija_carga = 544.0  # kWh/h
    ev_demand = np.zeros(len(ev_df))
    
    for i, (_, row) in enumerate(ev_df.iterrows()):
        hay_demanda = (row['vehicles_charging_motos'] > 0) or (row['vehicles_charging_mototaxis'] > 0)
        if hay_demanda:
            ev_demand[i] = demanda_fija_carga
        else:
            ev_demand[i] = 0.0
    
    return ev_demand


def extract_solar_generation(solar_df: pd.DataFrame) -> np.ndarray:
    """Extrae generación solar de pv_generation_hourly_citylearn_v2.csv."""
    # Buscar columna con generación (puede ser: 'Solar_kWh', 'solar_generation', etc.)
    
    possible_cols = ['Solar_kWh', 'solar_generation', 'pv_kwh', 'ac_power_kw', 'generation_kwh', 'energy_kwh']
    solar_col = None
    
    for col in possible_cols:
        if col in solar_df.columns:
            solar_col = col
            break
    
    if solar_col is None:
        # Usar última columna numérica
        solar_col = solar_df.select_dtypes(include=[np.number]).columns[-1]
    
    return solar_df[solar_col].values


def extract_mall_demand(mall_df: pd.DataFrame) -> np.ndarray:
    """Extrae demanda mall de demandamallhorakwh.csv."""
    # Buscar columna con demanda (puede ser: 'demanda_kwh', 'power_kw', 'mall_kwh', 'demand_kwh', etc.)
    
    possible_cols = ['demand_kwh', 'demanda_kwh', 'power_kw', 'mall_kwh', 'energy_kwh', 'kWh', 'kwh']
    mall_col = None
    
    for col in possible_cols:
        if col in mall_df.columns:
            mall_col = col
            break
    
    if mall_col is None:
        # Usar última columna numérica
        numeric_cols = mall_df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            mall_col = numeric_cols[-1]
        else:
            raise ValueError(f"No se encontró columna numérica en mall_df. Columnas: {mall_df.columns.tolist()}")
    
    return mall_df[mall_col].values


def simulate_annual(solar_gen: np.ndarray, ev_demand: np.ndarray, mall_demand: np.ndarray) -> pd.DataFrame:
    """
    Simula 1 año (8,760 horas) con lógica de control BESS CORRECTA.
    
    PRIORIDAD DE DESPACHO:
    1. SOLAR → EV (carga vehículos)
    2. EXCESO SOLAR → BESS (acumula energía)
    3. EXCESO FINAL → MALL (alimenta centro comercial)
    4. DEFICIT (noche) → BESS descarga para EV + GRID para MALL
    
    LÓGICA HORARIA:
    - 6-16h DIURNO: 
      * Solar carga EV (prioridad)
      * Exceso carga BESS hasta 100%
      * Sobrante alimenta MALL
    - 17-22h NOCTURNO:
      * BESS descarga para EV (complementa)
      * GRID alimenta lo que deja de haber
      * GRID alimenta MALL completo
    - 0-5, 23h MADRUGADA:
      * BESS en reposo (NO descarga)
      * GRID alimenta EV + MALL
    """
    
    bess = BESSSpecs()
    records = []
    
    # Initializar BESS en SOC mínimo (10%)
    soc_kwh = bess.reserve_capacity_kwh
    
    print(f"\n⚙️  Simulando {len(solar_gen)} horas (1 año)...")
    print("   Lógica: SOLAR → EV → BESS → MALL → GRID\n")
    
    start_date = datetime(2024, 1, 1, 0, 0, 0)
    
    for hour_idx in range(len(solar_gen)):
        timestamp = start_date + timedelta(hours=hour_idx)
        hour_of_day = timestamp.hour
        
        solar_kw = float(solar_gen[hour_idx])
        ev_kw = float(ev_demand[hour_idx])
        mall_kw = float(mall_demand[hour_idx])
        
        bess_charge_kwh = 0.0
        bess_discharge_kwh = 0.0
        grid_import_kwh = 0.0
        pv_to_ev = 0.0
        pv_to_bess = 0.0
        pv_to_mall = 0.0
        control_mode = "STANDBY"
        
        # ======== DIURNO (6-16h): PRIORIDAD SOLAR → EV → BESS → MALL ========
        if 6 <= hour_of_day <= 16:
            control_mode = "DIURNO"
            
            # PASO 1: Solar → EV
            pv_to_ev = min(solar_kw, ev_kw)
            ev_from_grid = ev_kw - pv_to_ev
            remaining_solar = solar_kw - pv_to_ev
            
            # PASO 2: Solar excedente → BESS (cargar hasta 100%)
            if remaining_solar > 0 and soc_kwh < bess.capacity_kwh:
                available_capacity = bess.capacity_kwh - soc_kwh
                max_charge_rate = min(bess.power_kw, remaining_solar)
                bess_charge_kwh = min(max_charge_rate, available_capacity)
                soc_kwh += bess_charge_kwh
                
                pv_to_bess = bess_charge_kwh
                remaining_solar -= bess_charge_kwh
            
            # PASO 3: Solar final → MALL
            pv_to_mall = min(remaining_solar, mall_kw)
            mall_from_grid = mall_kw - pv_to_mall
            
            # PASO 4: Lo que falta → GRID
            grid_import_kwh = ev_from_grid + mall_from_grid
        
        # ======== NOCTURNO (17-22h): BESS descarga para EV ========
        elif 17 <= hour_of_day <= 22:
            control_mode = "NOCTURNO"
            
            # BESS → EV (descarga para complementar)
            max_dischargeable = soc_kwh - bess.reserve_capacity_kwh
            ev_from_bess = min(ev_kw, max_dischargeable)
            bess_discharge_kwh = ev_from_bess
            soc_kwh -= bess_discharge_kwh
            
            # Complementar con GRID
            ev_from_grid = ev_kw - ev_from_bess
            grid_import_kwh = ev_from_grid + mall_kw
        
        # ======== MADRUGADA (0-5, 23h): GRID total ========
        else:
            control_mode = "MADRUGADA"
            # BESS en reposo, no descarga
            grid_import_kwh = ev_kw + mall_kw
        
        # Asegurar límites de SOC
        soc_kwh = np.clip(soc_kwh, bess.reserve_capacity_kwh, bess.capacity_kwh)
        soc_percent = (soc_kwh / bess.capacity_kwh) * 100.0
        
        record = {
            'timestamp': timestamp,
            'hour': hour_of_day,
            'solar_kw': solar_kw,
            'ev_demand_kw': ev_kw,
            'mall_demand_kw': mall_kw,
            'total_demand_kw': ev_kw + mall_kw,
            'pv_to_ev_kw': pv_to_ev,
            'pv_to_bess_kw': pv_to_bess,
            'pv_to_mall_kw': pv_to_mall,
            'bess_charge_kwh': bess_charge_kwh,
            'bess_discharge_kwh': bess_discharge_kwh,
            'bess_soc_kwh': soc_kwh,
            'bess_soc_percent': soc_percent,
            'grid_import_kwh': grid_import_kwh,
            'control_mode': control_mode,
        }
        records.append(record)
        
        # Progreso
        if (hour_idx + 1) % 730 == 0:  # Cada mes (~730 horas)
            print(f"   ✓ Procesadas {hour_idx + 1:,} horas ({(hour_idx + 1) / 8760 * 100:.1f}%)")
    
    return pd.DataFrame(records)


def main():
    print("\n" + "="*100)
    print("SIMULADOR BESS ANUAL - Datos Reales 2024 (8,760 horas)")
    print("="*100)
    
    # 1. Cargar perfiles
    solar_df, mall_df, ev_df = load_annual_profiles()
    
    # 2. Extraer datos
    print("\n📊 Extrayendo datos horarios...")
    solar_gen = extract_solar_generation(solar_df)
    mall_demand = extract_mall_demand(mall_df)
    ev_demand = extract_ev_demand(ev_df)
    print("   ✓ Datos extraídos")
    
    # Mostrar resumen
    print(f"\n📈 RESUMEN ENTRADA (8,760 horas):")
    print(f"   Solar: Total {solar_gen.sum():,.0f} kWh | Promedio {solar_gen.mean():.1f} kW/h | Pico {solar_gen.max():.0f} kW")
    print(f"   Mall:  Total {mall_demand.sum():,.0f} kWh | Promedio {mall_demand.mean():.1f} kW/h | Pico {mall_demand.max():.0f} kW")
    print(f"   EV:    Total {ev_demand.sum():,.0f} kWh | Promedio {ev_demand.mean():.1f} kW/h | Pico {ev_demand.max():.0f} kW")
    
    # 3. Simular 1 año
    print("\n⚙️  SIMULACIÓN ANUAL:")
    df = simulate_annual(solar_gen, ev_demand, mall_demand)
    print(f"   ✓ Simulación completada: {len(df):,} registros")
    
    # 4. Resumen anual
    print("\n" + "="*100)
    print("RESUMEN ANUAL (365 días)")
    print("="*100)
    
    total_solar = df['solar_kw'].sum()
    total_ev = df['ev_demand_kw'].sum()
    total_mall = df['mall_demand_kw'].sum()
    total_demand = total_ev + total_mall
    total_bess_charge = df['bess_charge_kwh'].sum()
    total_bess_discharge = df['bess_discharge_kwh'].sum()
    total_grid = df['grid_import_kwh'].sum()
    
    print(f"\n📈 ENERGÍAS (kWh):")
    print(f"   Generación Solar:        {total_solar:>15,.0f} kWh")
    print(f"   Demanda EV:              {total_ev:>15,.0f} kWh")
    print(f"   Demanda Mall:            {total_mall:>15,.0f} kWh")
    print(f"   Demanda Total:           {total_demand:>15,.0f} kWh")
    print(f"   Carga BESS:              {total_bess_charge:>15,.0f} kWh")
    print(f"   Descarga BESS:           {total_bess_discharge:>15,.0f} kWh")
    print(f"   Importación desde Grid:  {total_grid:>15,.0f} kWh")
    
    print(f"\n🔋 BESS ESTADÍSTICAS:")
    print(f"   SOC inicial: {df.iloc[0]['bess_soc_percent']:.1f}%")
    print(f"   SOC máximo:  {df['bess_soc_percent'].max():.1f}%")
    print(f"   SOC mínimo:  {df['bess_soc_percent'].min():.1f}%")
    print(f"   SOC final:   {df.iloc[-1]['bess_soc_percent']:.1f}%")
    print(f"   Ciclos/año:  {total_bess_charge / 3022.0:.2f}")
    print(f"   Ciclos/día:  {(total_bess_charge / 3022.0) / 365:.3f}")
    
    print(f"\n⚡ ÍNDICES DE RENDIMIENTO:")
    # Solar coverage = generación / demanda total
    solar_coverage = (total_solar / max(total_demand, 1)) * 100
    # EV satisfaction = cuánto de EV viene desde BESS (no de grid)
    ev_demand_covered_by_bess = total_bess_discharge / max(total_ev, 1) * 100
    # Autosufficiency = 1 - (grid / demanda total)
    self_sufficiency = (1.0 - total_grid / max(total_demand, 1)) * 100
    
    print(f"   Cobertura Solar:         {solar_coverage:.1f}%  (de {total_solar:,.0f} / {total_demand:,.0f} kWh)")
    print(f"   EV desde BESS:           {ev_demand_covered_by_bess:.1f}%  (de {total_bess_discharge:,.0f} / {total_ev:,.0f} kWh)")
    print(f"   Autosuficiencia:         {self_sufficiency:.1f}%  (sin grid: {total_demand - total_grid:,.0f} / {total_demand:,.0f} kWh)")
    
    # 5. Análisis mensual
    print(f"\n📊 ANÁLISIS MENSUAL:")
    df['month'] = df['timestamp'].dt.month
    
    for month in range(1, 13):
        month_data = df[df['month'] == month]
        month_names = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun',
                      7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
        
        sol = month_data['solar_kw'].sum()
        ev = month_data['ev_demand_kw'].sum()
        mal = month_data['mall_demand_kw'].sum()
        carga = month_data['bess_charge_kwh'].sum()
        desc = month_data['bess_discharge_kwh'].sum()
        grid = month_data['grid_import_kwh'].sum()
        
        print(f"   {month_names[month]}: Solar {sol:>8,.0f} | EV {ev:>8,.0f} | Mall {mal:>6,.0f} | "
              f"BESS +{carga:>6,.0f} -{desc:>6,.0f} | Grid {grid:>8,.0f}")
    
    # 6. Guardar datasets
    print("\n💾 Guardando datasets...")
    
    # Dataset solo BESS (para CityLearn)
    df_bess_only = df[['timestamp', 'bess_charge_kwh', 'bess_discharge_kwh', 'bess_soc_percent']].copy()
    output_bess = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
    df_bess_only.to_csv(output_bess, index=False)
    print(f"   ✓ BESS solo: {output_bess}")
    
    # Dataset completo (análisis detallado)
    output_full = Path('data/oe2/bess/bess_simulation_annual_2024.csv')
    df.to_csv(output_full, index=False)
    print(f"   ✓ Completo: {output_full}")
    
    # Guardar métricas
    metrics = {
        'total_hours': len(df),
        'total_solar_kwh': float(total_solar),
        'total_ev_demand_kwh': float(total_ev),
        'total_mall_demand_kwh': float(total_mall),
        'total_demand_kwh': float(total_demand),
        'total_bess_charge_kwh': float(total_bess_charge),
        'total_bess_discharge_kwh': float(total_bess_discharge),
        'total_grid_import_kwh': float(total_grid),
        'solar_coverage_percent': float(solar_coverage),
        'ev_from_bess_percent': float(ev_demand_covered_by_bess),
        'self_sufficiency_percent': float(self_sufficiency),
        'cycles_per_year': float(total_bess_charge / 3022.0),
        'cycles_per_day': float((total_bess_charge / 3022.0) / 365),
        'soc_min_percent': float(df['bess_soc_percent'].min()),
        'soc_max_percent': float(df['bess_soc_percent'].max()),
        'soc_initial_percent': float(df.iloc[0]['bess_soc_percent']),
        'soc_final_percent': float(df.iloc[-1]['bess_soc_percent']),
    }
    
    metrics_file = Path('data/oe2/bess/simulation_metrics_annual_2024.json')
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"   ✓ Métricas: {metrics_file}")
    
    print("\n" + "="*100)
    print("✅ Simulación ANUAL completada")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
