#!/usr/bin/env python3
"""
CORRECCIÓN DE CÁLCULO CO₂ DIRECTO E INDIRECTO

CO₂ DIRECTO = Reducción modal: EVs cargados × Emisión diesel de moto/mototaxi
  - Energía NO importa, sino CANTIDAD de vehículos que dejan de usar combustible
  - Mientras más EVs se cargan, mayor CO₂ directo evitado

CO₂ INDIRECTO = Fuente de energía para cargar ESE EV:
  - Solar generada × 0.4521 (evita diesel en grid)
  - BESS descargada × 0.4521 (evita diesel en grid)
"""

import pandas as pd
import numpy as np
from pathlib import Path

print(f"""
════════════════════════════════════════════════════════════════════════════════
🔍 ANÁLISIS CORRECTO: CO₂ DIRECTO (MODAL) + CO₂ INDIRECTO (FUENTE ENERGÍA)
════════════════════════════════════════════════════════════════════════════════
""")

# Factores de emisión
FACTOR_CO2_MOTO_DIESEL_ANUAL = 1.2  # kg CO₂/año por moto que circularía con diesel
FACTOR_CO2_MOTOTAXI_DIESEL_ANUAL = 2.1  # kg CO₂/año por mototaxi que circularía con diesel
FACTOR_CO2_THERMAL_GRID = 0.4521  # kg CO₂/kWh de generación térmica

# Datos de flota
MOTOS_CIRCULATING = 270  # motos por día
MOTOTAXIS_CIRCULATING = 39  # mototaxis por día

MOTOS_PER_CHARGER = 15  # 15 chargers para motos
MOTOTAXIS_PER_CHARGER = 4  # 4 chargers para mototaxis

# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def get_agent_timeseries_path(agent_name):
    """Obtiene ruta del CSV de timeseries del agente"""
    agent_lower = agent_name.lower()
    return Path(f'outputs/{agent_lower}_training/timeseries_{agent_lower}.csv')

def calculate_co2_metrics(agent_name, timeseries_df):
    """
    Calcula CO₂ directo e indirecto correctamente
    
    CO₂ DIRECTO: Basado en cantidad de EVs cargados (cambio modal)
    CO₂ INDIRECTO: Basado en fuente de energía (solar + BESS)
    """
    
    print(f"\n📊 ANALIZANDO {agent_name}:")
    print(f"   Records: {len(timeseries_df)}")
    
    # Verificar columnas disponibles
    cols = timeseries_df.columns.tolist()
    print(f"   Columnas: {cols[:10]}...")
    
    has_ev_charging = 'ev_charging_kw' in cols
    has_solar = 'solar_kw' in cols
    has_bess = 'bess_power_kw' in cols
    
    print(f"   - ev_charging_kw: {has_ev_charging}")
    print(f"   - solar_kw: {has_solar}")
    print(f"   - bess_power_kw: {has_bess}")
    
    daily_metrics = []
    
    num_days = len(timeseries_df) // 24
    
    for day_idx in range(num_days):
        start = day_idx * 24
        end = start + 24
        
        day_data = timeseries_df.iloc[start:end]
        
        # ================================================================
        # CO₂ DIRECTO: Cantidad de EVs cargados
        # ================================================================
        
        if has_ev_charging:
            # Total energía cargada ese día (kWh)
            ev_energy_kwh = pd.to_numeric(day_data['ev_charging_kw'], errors='coerce').fillna(0).sum()
            
            # Estimar cantidad de EVs cargados
            # Asumiendo que cada carga completa es ~30 kWh (batería típica eléctrica)
            charge_per_ev = 30  # kWh
            num_evs_charged = max(0, ev_energy_kwh / charge_per_ev)
            
            # Aproximar mix de motos/mototaxis (80% motos, 20% mototaxis)
            num_motos_charged = num_evs_charged * 0.80
            num_mototaxis_charged = num_evs_charged * 0.20
            
            # CO₂ directo = cambio modal
            co2_direct_daily = (num_motos_charged * FACTOR_CO2_MOTO_DIESEL_ANUAL / 365 + 
                              num_mototaxis_charged * FACTOR_CO2_MOTOTAXI_DIESEL_ANUAL / 365)
        else:
            num_evs_charged = 0
            co2_direct_daily = 0
        
        # ================================================================
        # CO₂ INDIRECTO: Fuente de energía
        # ================================================================
        
        # Solar generada
        if has_solar:
            solar_energy = pd.to_numeric(day_data['solar_kw'], errors='coerce').fillna(0).sum()
        else:
            solar_energy = 0
        
        # BESS descargada (solo positivo = discharge)
        if has_bess:
            bess_power = pd.to_numeric(day_data['bess_power_kw'], errors='coerce').fillna(0).values
            bess_discharged = np.sum(bess_power[bess_power > 0])  # Solo discharge
        else:
            bess_discharged = 0
        
        # CO₂ indirecto = energía renovable/almacenada × factor de evitar diesel
        renewable_energy = solar_energy + bess_discharged
        co2_indirect_daily = renewable_energy * FACTOR_CO2_THERMAL_GRID
        
        # ================================================================
        # ALMACENAR MÉTRICAS DIARIAS
        # ================================================================
        
        daily_metrics.append({
            'day': day_idx + 1,
            'ev_energy_kwh': ev_energy_kwh,
            'num_evs_charged': num_evs_charged,
            'solar_kwh': solar_energy,
            'bess_discharged_kwh': bess_discharged,
            'renewable_total_kwh': renewable_energy,
            'co2_direct_kg': co2_direct_daily,
            'co2_indirect_kg': co2_indirect_daily,
            'co2_total_kg': co2_direct_daily + co2_indirect_daily,
        })
    
    daily_df = pd.DataFrame(daily_metrics)
    
    # ================================================================
    # ESTADÍSTICAS FINALES
    # ================================================================
    
    print(f"\n   📈 ESTADÍSTICAS {agent_name}:")
    print(f"   - Días analizados: {len(daily_df)}")
    print(f"   - EVs cargados promedio/día: {daily_df['num_evs_charged'].mean():.2f}")
    print(f"   - Energía EV promedio/día: {daily_df['ev_energy_kwh'].mean():.1f} kWh")
    print(f"   - Solar promedio/día: {daily_df['solar_kwh'].mean():.1f} kWh")
    print(f"   - BESS descargado promedio/día: {daily_df['bess_discharged_kwh'].mean():.1f} kWh")
    print(f"   - CO₂ directo total: {daily_df['co2_direct_kg'].sum():.1f} kg")
    print(f"   - CO₂ indirecto total: {daily_df['co2_indirect_kg'].sum():.1f} kg")
    print(f"   - CO₂ total evitado: {daily_df['co2_total_kg'].sum():.1f} kg")
    
    # Comparar inicio vs final
    n_period = max(int(len(daily_df) * 0.1), 50)
    initial = daily_df.iloc[:n_period]
    final = daily_df.iloc[-n_period:]
    
    print(f"\n   📊 COMPARACIÓN INICIO vs FINAL (primera/última 10%):")
    print(f"   EVs cargados/día:")
    print(f"      Inicio: {initial['num_evs_charged'].mean():.2f} → Final: {final['num_evs_charged'].mean():.2f}")
    print(f"   CO₂ directo kgs/día:")
    print(f"      Inicio: {initial['co2_direct_kg'].mean():.2f} → Final: {final['co2_direct_kg'].mean():.2f}")
    print(f"   CO₂ indirecto kg/día:")
    print(f"      Inicio: {initial['co2_indirect_kg'].mean():.2f} → Final: {final['co2_indirect_kg'].mean():.2f}")
    
    return daily_df

# ============================================================================
# ANALIZAR TODOS LOS AGENTES
# ============================================================================

agents = ['SAC', 'PPO', 'A2C']
all_results = {}

for agent_name in agents:
    ts_path = get_agent_timeseries_path(agent_name)
    
    if not ts_path.exists():
        print(f"\n❌ {agent_name}: No encontrado en {ts_path}")
        continue
    
    try:
        df = pd.read_csv(ts_path)
        metrics_df = calculate_co2_metrics(agent_name, df)
        all_results[agent_name] = metrics_df
    except Exception as e:
        print(f"\n❌ Error procesando {agent_name}: {e}")

# ============================================================================
# COMPARACIÓN CONSOLIDADA
# ============================================================================

print(f"""
════════════════════════════════════════════════════════════════════════════════
📋 RESUMEN COMPARATIVO: CO₂ DIRECTO (MODAL) vs CO₂ INDIRECTO (ENERGÍA)
════════════════════════════════════════════════════════════════════════════════
""")

comparison_rows = []
for agent_name in agents:
    if agent_name not in all_results:
        continue
    
    df = all_results[agent_name]
    n_period = max(int(len(df) * 0.1), 50)
    
    initial = df.iloc[:n_period]
    final = df.iloc[-n_period:]
    
    co2_dir_initial = initial['co2_direct_kg'].mean()
    co2_dir_final = final['co2_direct_kg'].mean()
    co2_dir_change = ((co2_dir_final - co2_dir_initial) / (co2_dir_initial + 0.001)) * 100
    
    co2_ind_initial = initial['co2_indirect_kg'].mean()
    co2_ind_final = final['co2_indirect_kg'].mean()
    co2_ind_change = ((co2_ind_final - co2_ind_initial) / (co2_ind_initial + 0.001)) * 100
    
    total_co2_avoided = df['co2_total_kg'].sum()
    total_days = len(df)
    total_evs_charged = df['num_evs_charged'].sum()
    
    comparison_rows.append({
        'Agent': agent_name,
        'Days': total_days,
        'Total EVs': f"{total_evs_charged:.0f}",
        'CO₂ Directo (kg)': f"{total_co2_avoided:,.1f}",
        'CO₂ Indirecto (kg)': f"{df['co2_indirect_kg'].sum():,.1f}",
        'Cambio CO₂D': f"{co2_dir_change:+.1f}%",
        'Cambio CO₂I': f"{co2_ind_change:+.1f}%"
    })

comparison_df = pd.DataFrame(comparison_rows)
print("\n")
print(comparison_df.to_string(index=False))

print(f"""
════════════════════════════════════════════════════════════════════════════════

INTERPRETACIÓN:
  CO₂ DIRECTO (🔴): Cantidad de motos/mototaxis que pasaron de diesel a EV
    - Factor: {FACTOR_CO2_MOTO_DIESEL_ANUAL} kg CO₂/año moto diesel
    - Factor: {FACTOR_CO2_MOTOTAXI_DIESEL_ANUAL} kg CO₂/año mototaxi diesel
    
  CO₂ INDIRECTO (🟢): Energía renovable usada para cargar esos EVs
    - Solar generada × {FACTOR_CO2_THERMAL_GRID} kg CO₂/kWh evitado
    - BESS descargada × {FACTOR_CO2_THERMAL_GRID} kg CO₂/kWh evitado
    
  TOTAL = Impacto ambiental real del agente

════════════════════════════════════════════════════════════════════════════════
""")

# Guardar resultados detallados
output_dir = Path('outputs/analysis')
output_dir.mkdir(parents=True, exist_ok=True)

for agent_name, df in all_results.items():
    output_file = output_dir / f'{agent_name.lower()}_co2_analysis.csv'
    df.to_csv(output_file, index=False)
    print(f"✓ Guardado: {output_file}")

print("\n✅ ANÁLISIS COMPLETADO\n")
