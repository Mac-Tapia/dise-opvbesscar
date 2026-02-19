#!/usr/bin/env python3
"""
Script de validación de integración del perfil EV en balance.py
Verifica que los datos desde chargers.py se reflejen correctamente en el balance energético.

Uso:
    python validate_ev_balance_integration.py
"""

import sys
from pathlib import Path

# Agregar ruta del proyecto
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from src.dimensionamiento.oe2.balance_energetico.ev_profile_integration import (
    validate_ev_csv_profile,
    print_ev_profile_summary,
    calculate_ev_demand_theoretical,
    get_operational_factor,
    MOTO_SPEC,
    MOTOTAXI_SPEC,
    CHARGING_EFFICIENCY,
)


def main():
    print("\n" + "="*80)
    print("VALIDACIÓN DE INTEGRACIÓN DEL PERFIL EV (chargers.py → balance.py)")
    print("="*80)
    
    # Paso 1: Cargar CSV de chargers
    chargers_path = project_root / "data/oe2/chargers/chargers_ev_ano_2024_v3.csv"
    
    if not chargers_path.exists():
        print(f"\n✗ ERROR: No se encontró archivo de chargers en {chargers_path}")
        return False
    
    print(f"\n[PASO 1/4] Cargando dataset de chargers...")
    try:
        df = pd.read_csv(chargers_path, index_col=0, nrows=8760)
        print(f"  ✓ Dataset cargado: {df.shape[0]} filas × {df.shape[1]} columnas")
    except Exception as e:
        print(f"  ✗ Error al cargar: {e}")
        return False
    
    # Paso 2: Calcular demanda teórica
    print(f"\n[PASO 2/4] Calculando demanda teórica...")
    demand = calculate_ev_demand_theoretical()
    print(f"  Energía teórica diaria: {demand['total_daily_kwh']:,.1f} kWh")
    print(f"  Energía teórica anual: {demand['total_annual_kwh']:,.0f} kWh")
    
    # Paso 3: Validar perfil EV
    print(f"\n[PASO 3/4] Validando perfil EV desde CSV...")
    validation = validate_ev_csv_profile(df, expected_annual_kwh=demand['total_annual_kwh'])
    
    if validation['valid']:
        print(f"  ✓ VALIDACIÓN EXITOSA - Perfil EV conforme")
    else:
        print(f"  ✗ VALIDACIÓN FALLÓ - Se encontraron errores:")
        for err in validation['errors']:
            print(f"     - {err}")
    
    if validation['warnings']:
        print(f"  ⚠️  Advertencias ({len(validation['warnings'])}):")
        for warn in validation['warnings']:
            print(f"     - {warn}")
    
    # Paso 4: Mostrar resumen
    print(f"\n[PASO 4/4] Resumen de validación...")
    print_ev_profile_summary(df)
    
    # Verificaciones adicionales
    print(f"\n[VERIFICACIONES ADICIONALES]:")
    
    # A. Factor operacional por hora
    print(f"\n  A. FACTORES OPERACIONALES (malliquitos, 9h-22h):")
    hours_to_check = [8, 9, 10, 17, 18, 19, 20, 21, 22]
    for h in hours_to_check:
        factor = get_operational_factor(h)
        print(f"     {h:2d}h: {factor*100:5.1f}%")
    
    # B. Energía por hora tipo
    print(f"\n  B. ENERGÍA POR HORA (muestreo):")
    power_cols = [col for col in df.columns if 'charging_power_kw' in col]
    df_hourly = df[power_cols].sum(axis=1)
    
    for h in hours_to_check:
        indices = df.index.hour == h
        if indices.sum() > 0:
            energias = df_hourly[indices]
            print(f"     {h:2d}h: min={energias.min():.1f}, max={energias.max():.1f}, "
                  f"promedio={energias.mean():.1f} kW")
    
    # C. Especificaciones de vehículos
    print(f"\n  C. ESPECIFICACIONES DE VEHÍCULOS (desde chargers.py):")
    print(f"     MOTOS:")
    print(f"       - Capacidad batería: {MOTO_SPEC.battery_kwh} kWh")
    print(f"       - Energía por carga: {MOTO_SPEC.energy_to_charge_kwh:.3f} kWh")
    print(f"       - Cantidad/día: {MOTO_SPEC.quantity_per_day} vehículos")
    print(f"       - Cargadores: {MOTO_SPEC.chargers_assigned} × 2 = {MOTO_SPEC.sockets_assigned} sockets")
    print(f"     MOTOTAXIS:")
    print(f"       - Capacidad batería: {MOTOTAXI_SPEC.battery_kwh} kWh")
    print(f"       - Energía por carga: {MOTOTAXI_SPEC.energy_to_charge_kwh:.3f} kWh")
    print(f"       - Cantidad/día: {MOTOTAXI_SPEC.quantity_per_day} vehículos")
    print(f"       - Cargadores: {MOTOTAXI_SPEC.chargers_assigned} × 2 = {MOTOTAXI_SPEC.sockets_assigned} sockets")
    
    # D. Eficiencia real
    print(f"\n  D. EFICIENCIA DE CARGA:")
    print(f"     - Potencia nominal: 7.4 kW/toma × 38 tomas = 281.2 kW")
    print(f"     - Eficiencia real: {CHARGING_EFFICIENCY*100:.0f}% (incluye pérdidas)")
    print(f"     - Potencia efectiva: 7.4 × {CHARGING_EFFICIENCY} = {7.4*CHARGING_EFFICIENCY:.2f} kW/toma")
    print(f"     - Máximo teórico: 281.2 × {CHARGING_EFFICIENCY} = {281.2*CHARGING_EFFICIENCY:.1f} kW")
    
    # E. Sincronización con balance.py
    print(f"\n  E. VARIABLES PARA INTEGRACIÓN CON BALANCE.PY:")
    print(f"     - energy_motos_kwh: {validation['metrics'].get('energy_motos_kwh', 0):,.0f}")
    print(f"     - energy_taxis_kwh: {validation['metrics'].get('energy_taxis_kwh', 0):,.0f}")
    print(f"     - total_energy_annual: {validation['metrics'].get('total_energy_annual_kwh', 0):,.0f}")
    print(f"     - ratio_motos_taxis: {validation['metrics'].get('ratio_motos_taxis_actual', 0):.2f}")
    print(f"     - punta_concentration: {validation['metrics'].get('energy_punta_pct', 0):.1f}%")
    print(f"     - max_power_actual: {validation['metrics'].get('max_power_actual_kw', 0):.1f} kW")
    
    print("\n" + "="*80)
    print("VALIDACIÓN COMPLETADA")
    print("="*80 + "\n")
    
    return validation['valid']


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
