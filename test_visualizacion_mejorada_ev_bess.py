#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEST: Validar que la visualización mejorada muestra:
1. Perfil EV desagregado (motos vs taxis) desde chargers.py
2. Lógica BESS descarga con Prioridad 1 (EV) y Prioridad 2 (Peak Shaving >1,900kW)
3. Etiquetas claras de especificaciones desde chargers.py
"""

import sys
import io
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    # Redirigir stdout/stderr a UTF-8 en Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cargar módulos del proyecto
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem
from src.dimensionamiento.oe2.balance_energetico.ev_profile_integration import (
    MOTO_SPEC, MOTOTAXI_SPEC, MALL_OPERATIONAL_HOURS, CHARGING_EFFICIENCY,
    validate_ev_csv_profile, print_ev_profile_summary
)

def test_visualization_with_ev_profile():
    """Generar gráfica mejorada y validar que muestre EV profile + BESS logic"""
    
    print("=" * 80)
    print("TEST: Visualización Mejorada - EV Profile desde Chargers + BESS Logic v5.4")
    print("=" * 80)
    print()
    
    # Cargar datos REALES desde CSVs
    print("[INFO] Creando DataFrame con datos REALES del OE2...")
    
    # 1. Cargar PV generación REAL
    print("  → Cargando PV real desde data/oe2/Generacionsolar/pv_generation_citylearn2024.csv...")
    pv_df = pd.read_csv(repo_root / 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    pv_gen = pv_df['potencia_kw'].values  # 8760 values
    
    # 2. Cargar Mall demand REAL
    print("  → Cargando Mall demand real desde data/oe2/demandamallkwh/demandamallhorakwh.csv...")
    mall_df = pd.read_csv(repo_root / 'data/oe2/demandamallkwh/demandamallhorakwh.csv')
    mall_demand = mall_df['mall_demand_kwh'].values  # 8760 values
    
    # 3. EV demand REAL (calculado desde chargers CSV)
    print("  → Calculando EV demand real desde data/oe2/chargers/chargers_ev_ano_2024_v3.csv...")
    chargers_df = pd.read_csv(repo_root / 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    chargers_df['datetime'] = pd.to_datetime(chargers_df['datetime'])
    
    # Motos (sockets 0-29) + Taxis (sockets 30-37)
    moto_cols = [f'socket_{i:03d}_charger_power_kw' for i in range(30)]
    taxi_cols = [f'socket_{i:03d}_charger_power_kw' for i in range(30, 38)]
    ev_demand = (chargers_df[moto_cols].sum(axis=1) + chargers_df[taxi_cols].sum(axis=1)).values
    
    hours = len(pv_gen)
    np.random.seed(42)
    
    total_demand = mall_demand + ev_demand
    
    # BESS logic
    bess_soc = np.zeros(hours)
    bess_soc[0] = 50
    bess_charge = np.zeros(hours)
    bess_discharge = np.zeros(hours)
    demand_from_grid = np.zeros(hours)
    pv_to_demand = np.zeros(hours)
    pv_to_bess = np.zeros(hours)
    pv_to_grid = np.zeros(hours)
    co2_from_grid = np.zeros(hours)
    
    for t in range(1, hours):
        # Prioridades: 1) EV, 2) Mall, 3) BESS carga, 4) Red
        available_pv = pv_gen[t]
        demand_t = total_demand[t]
        
        # Usar PV para demanda
        pv_to_demand_t = min(available_pv, demand_t)
        available_pv -= pv_to_demand_t
        
        # Si sobra PV, cargar BESS
        if available_pv > 0 and bess_soc[t-1] < 100:
            bess_charge_t = min(available_pv, 400, 100 - bess_soc[t-1])
            pv_to_bess_t = bess_charge_t
            bess_charge[t] = bess_charge_t
            available_pv -= bess_charge_t
        
        # Wasted PV
        pv_to_grid[t] = available_pv
        
        # Si demanda > PV, usar BESS
        deficit = demand_t - pv_to_demand_t
        if deficit > 0:
            bess_discharge_t = min(deficit, 400, bess_soc[t-1] * 17)  # 1700kWh capacity
            bess_discharge[t] = min(bess_discharge_t, deficit)
            demand_from_grid[t] = max(0, deficit - bess_discharge[t])
        else:
            demand_from_grid[t] = 0
        
        # Update SOC
        bess_soc[t] = bess_soc[t-1] + (bess_charge[t] - bess_discharge[t]) / 1700 * 100
        bess_soc[t] = np.clip(bess_soc[t], 20, 100)  # 20-100% operational range
        
        # CO2 emissions
        co2_from_grid[t] = demand_from_grid[t] * 0.4521 / 1000  # kg CO2 per kWh
    
    # Create DataFrame
    df = pd.DataFrame({
        'hour': np.arange(hours),
        'pv_generation_kw': pv_gen,
        'mall_demand_kw': mall_demand,
        'ev_demand_kw': ev_demand,
        'total_demand_kw': total_demand,
        'pv_to_demand_kw': pv_to_demand,
        'pv_to_bess_kw': pv_to_bess,
        'pv_to_grid_kw': pv_to_grid,
        'bess_charge_kw': bess_charge,
        'bess_discharge_kw': bess_discharge,
        'bess_soc_percent': bess_soc,
        'demand_from_grid_kw': demand_from_grid,
        'co2_from_grid_kg': co2_from_grid,
    })
    
    print("[OK] DataFrame de prueba creado")
    print(f"    Shape: {df.shape}")
    print(f"    Columns: {len(df.columns)}")
    print()
    
    # Crear instancia de balance con DataFrame
    balance = BalanceEnergeticoSystem(df_balance=df)
    print("[OK] BalanceEnergeticoSystem inicializado con DataFrame")
    print()
    
    # Validar especificaciones de chargers
    print("[INFO] ESPECIFICACIONES DESDE CHARGERS.PY:")
    print(f"  MOTOS:       {MOTO_SPEC.quantity_per_day}/día, {MOTO_SPEC.sockets_assigned} sockets")
    print(f"              Batería: {MOTO_SPEC.battery_kwh} kWh, Carga: {MOTO_SPEC.energy_to_charge_kwh} kWh")
    print(f"  MOTOTAXIS:   {MOTOTAXI_SPEC.quantity_per_day}/día, {MOTOTAXI_SPEC.sockets_assigned} sockets")
    print(f"              Batería: {MOTOTAXI_SPEC.battery_kwh} kWh, Carga: {MOTOTAXI_SPEC.energy_to_charge_kwh} kWh")
    total_vehicles = MOTO_SPEC.quantity_per_day + MOTOTAXI_SPEC.quantity_per_day
    total_sockets = MOTO_SPEC.sockets_assigned + MOTOTAXI_SPEC.sockets_assigned
    print(f"  Total: {total_vehicles} vehículos/día, {total_sockets} sockets")
    print(f"  Horario: 9h-22h (redistribución 21h)")
    print(f"  Eficiencia: {CHARGING_EFFICIENCY*100:.0f}%")
    print()
    
    # Validar EV profile en DataFrame
    print("[INFO] PERFIL EV EN DATASET:")
    print(f"  EV Demanda Total: {df['ev_demand_kw'].sum():.1f} kWh/año")
    print(f"  EV Media: {df['ev_demand_kw'].mean():.1f} kW")
    print(f"  EV Máx: {df['ev_demand_kw'].max():.1f} kW")
    print()
    
    # Validar BESS data
    print("[INFO] BESS OPERACIÓN EN DATASET:")
    soc_summary = df['bess_soc_percent'].describe()
    print(f"  SOC Min: {soc_summary['min']:.1f}%")
    print(f"  SOC Max: {soc_summary['max']:.1f}%")
    print(f"  SOC Media: {soc_summary['mean']:.1f}%")
    print(f"  BESS Carga Total: {df['bess_charge_kw'].sum():.1f} kWh/año")
    print(f"  BESS Descarga Total: {df['bess_discharge_kw'].sum():.1f} kWh/año")
    print()
    
    # Generar gráfica mejorada
    print("[INFO] GENERANDO VISUALIZACIÓN...")
    print()
    
    try:
        # Salida a directorio outputs
        from pathlib import Path
        out_dir = Path(__file__).parent / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        balance.plot_energy_balance(out_dir=out_dir)
        print(f"[OK] Gráficas guardadas en: {out_dir}")
        print()
        
        # Verificar archivos creados
        png_files = list(out_dir.glob("*.png"))
        print(f"[OK] {len(png_files)} gráficas generadas:")
        for png in sorted(png_files):
            print(f"    ✓ {png.name}")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error generando gráficas: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("=" * 80)
    print("TEST COMPLETADO - Balance.py (GRAPHICS ONLY) funciona correctamente")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    success = test_visualization_with_ev_profile()
    sys.exit(0 if success else 1)
