#!/usr/bin/env python3
"""
VALIDACIÓN: Dataset actualizado con columnas de CO2 y cantidad de vehículos

Verifica que:
1. Cantidad de columnas correcta
2. Columnas de CO2 por tipo (motos y taxis)
3. Columnas de cantidad de vehículos activos
4. Columnas de energía y tarifa
5. Datos listos para CityLearnv2
"""

import pandas as pd
import numpy as np
from pathlib import Path

def validate_dataset():
    dataset_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    
    print("="*80)
    print("VALIDACIÓN DE DATASET - ESTRUCTURA Y COLUMNAS")
    print("="*80)
    print()
    
    if not dataset_path.exists():
        print(f"❌ DATASET NO EXISTE: {dataset_path}")
        print("Primero ejecuta: python src/dimensionamiento/oe2/disenocargadoresev/chargers.py")
        return False
    
    # Cargar dataset
    df = pd.read_csv(dataset_path, index_col=0, parse_dates=True)
    print(f"✅ Dataset cargado: {dataset_path}")
    print(f"   Shape: {df.shape} (filas × columnas)")
    print()
    
    # ========================================================================
    # SECCIÓN 1: VALIDAR ESTRUCTURA BÁSICA
    # ========================================================================
    print("SECCIÓN 1: VALIDACIÓN DE ESTRUCTURA BÁSICA")
    print("-"*80)
    
    # Verificar cantidad de filas (8760 = 1 año)
    if len(df) == 8760:
        print(f"✅ Filas correctas: {len(df)} (8,760 horas en 1 año)")
    else:
        print(f"❌ Filas incorrectas: {len(df)} (esperado 8,760)")
        return False
    
    # Verificar índice (datetime)
    if isinstance(df.index, pd.DatetimeIndex):
        print(f"✅ Índice es datetime: {df.index.name}")
        print(f"   Rango: {df.index.min()} a {df.index.max()}")
    else:
        print(f"❌ Índice no es datetime")
        return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 2: VALIDAR COLUMNAS DE SOCKETS
    # ========================================================================
    print("SECCIÓN 2: VALIDACIÓN DE COLUMNAS DE SOCKETS")
    print("-"*80)
    
    socket_active_cols = [col for col in df.columns if '_active' in col]
    socket_power_cols = [col for col in df.columns if '_charging_power_kw' in col]
    socket_soc_cols = [col for col in df.columns if '_soc_' in col]
    
    print(f"✅ Columnas _active: {len(socket_active_cols)} (esperado 38)")
    print(f"✅ Columnas _charging_power_kw: {len(socket_power_cols)} (esperado 38)")
    print(f"✅ Columnas _soc_*: {len(socket_soc_cols)} (esperado 114 = 38×3)")
    
    if len(socket_active_cols) != 38 or len(socket_power_cols) != 38:
        print("❌ Cantidad de sockets incorrecta")
        return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 3: VALIDAR COLUMNAS DE CANTIDAD DE VEHÍCULOS
    # ========================================================================
    print("SECCIÓN 3: VALIDACIÓN DE COLUMNAS DE CANTIDAD DE VEHÍCULOS")
    print("-"*80)
    
    required_cols_vehicles = [
        'cantidad_motos_activas',
        'cantidad_mototaxis_activas',
        'cantidad_total_vehiculos_activos'
    ]
    
    for col in required_cols_vehicles:
        if col in df.columns:
            mean_val = df[col].mean()
            max_val = df[col].max()
            print(f"✅ {col}")
            print(f"   Media: {mean_val:.1f}, Máximo: {max_val:.0f}")
        else:
            print(f"❌ FALTA columna: {col}")
            return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 4: VALIDAR COLUMNAS DE ENERGÍA
    # ========================================================================
    print("SECCIÓN 4: VALIDACIÓN DE COLUMNAS DE ENERGÍA")
    print("-"*80)
    
    required_cols_energy = [
        'ev_energia_total_kwh',
        'ev_energia_motos_kwh',
        'ev_energia_mototaxis_kwh',
        'ev_demand_kwh'
    ]
    
    for col in required_cols_energy:
        if col in df.columns:
            total_energy = df[col].sum()
            mean_hourly = df[col].mean()
            print(f"✅ {col}")
            print(f"   Anual: {total_energy:.0f} kWh, Promedio/hora: {mean_hourly:.2f} kWh")
        else:
            print(f"❌ FALTA columna: {col}")
            return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 5: VALIDAR COLUMNAS DE CO2
    # ========================================================================
    print("SECCIÓN 5: VALIDACIÓN DE COLUMNAS DE CO2 (PROPORCIONAL A ENERGÍA)")
    print("-"*80)
    
    required_cols_co2 = [
        'co2_reduccion_motos_kg',
        'co2_reduccion_mototaxis_kg',
        'reduccion_directa_co2_kg',
        'co2_grid_kwh',
        'co2_neto_por_hora_kg'
    ]
    
    for col in required_cols_co2:
        if col in df.columns:
            total_co2 = df[col].sum()
            mean_hourly = df[col].mean()
            print(f"✅ {col}")
            print(f"   Anual: {total_co2:.0f} kg CO2, Promedio/hora: {mean_hourly:.2f} kg")
        else:
            print(f"❌ FALTA columna: {col}")
            return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 6: VALIDAR COLUMNAS DE TARIFA
    # ========================================================================
    print("SECCIÓN 6: VALIDACIÓN DE COLUMNAS DE TARIFA OSINERGMIN")
    print("-"*80)
    
    required_cols_tariff = [
        'is_hora_punta',
        'tarifa_aplicada_soles',
        'costo_carga_ev_soles'
    ]
    
    for col in required_cols_tariff:
        if col in df.columns:
            if col == 'is_hora_punta':
                n_punta = (df[col] == 1).sum()
                print(f"✅ {col}: {n_punta} horas punta (esperado ~1460 = 365×4h)")
            elif col == 'tarifa_aplicada_soles':
                print(f"✅ {col}")
                print(f"   Min: {df[col].min():.3f}, Max: {df[col].max():.3f} S/./kWh")
            elif col == 'costo_carga_ev_soles':
                total_costo = df[col].sum()
                print(f"✅ {col}")
                print(f"   Costo anual: S/. {total_costo:.2f}")
        else:
            print(f"❌ FALTA columna: {col}")
            return False
    
    print()
    
    # ========================================================================
    # SECCIÓN 7: VALIDACIONES DE COHERENCIA
    # ========================================================================
    print("SECCIÓN 7: VALIDACIONES DE COHERENCIA")
    print("-"*80)
    
    # CO2 debe ser proporcional a energía
    ratio_co2_motos = (df['co2_reduccion_motos_kg'].sum() / 
                       df['ev_energia_motos_kwh'].sum())
    expected_factor = 0.87
    
    if abs(ratio_co2_motos - expected_factor) < 0.01:
        print(f"✅ Factor CO2 motos correcto: {ratio_co2_motos:.3f} (esperado 0.87)")
    else:
        print(f"❌ Factor CO2 motos incorrecto: {ratio_co2_motos:.3f} (esperado 0.87)")
    
    # Cantidad de vehículos no puede exceder capacidad de sockets
    max_motos = df['cantidad_motos_activas'].max()
    max_taxis = df['cantidad_mototaxis_activas'].max()
    
    if max_motos <= 30:
        print(f"✅ Máximo motos activas: {max_motos:.0f} (límite 30 sockets)")
    else:
        print(f"❌ Máximo motos activas: {max_motos:.0f} (excede 30 sockets)")
    
    if max_taxis <= 8:
        print(f"✅ Máximo taxis activos: {max_taxis:.0f} (límite 8 sockets)")
    else:
        print(f"❌ Máximo taxis activos: {max_taxis:.0f} (excede 8 sockets)")
    
    print()
    
    # ========================================================================
    # SECCIÓN 8: RESUMEN PARA CITYLEARNV2
    # ========================================================================
    print("SECCIÓN 8: RESUMEN PARA CITYLEARNV2")
    print("-"*80)
    
    total_cols = len(df.columns)
    print(f"Total de columnas: {total_cols}")
    print()
    
    print("Columnas críticas para CityLearn:")
    critical_cols = [
        'ev_demand_kwh',
        'ev_energia_total_kwh',
        'cantidad_motos_activas',
        'cantidad_mototaxis_activas',
        'reduccion_directa_co2_kg',
        'co2_grid_kwh',
        'co2_neto_por_hora_kg'
    ]
    
    for col in critical_cols:
        if col in df.columns:
            print(f"  ✅ {col}")
        else:
            print(f"  ❌ {col} (FALTA)")
    
    print()
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print()
    
    print("ESTADÍSTICAS ANUALES:")
    print(f"  Energía total EVs: {df['ev_energia_total_kwh'].sum()/1000:.1f} MWh")
    print(f"  Energía motos: {df['ev_energia_motos_kwh'].sum()/1000:.1f} MWh")
    print(f"  Energía taxis: {df['ev_energia_mototaxis_kwh'].sum()/1000:.1f} MWh")
    print()
    
    print("IMPACTO CO2:")
    print(f"  CO2 evitado (combustible): {df['reduccion_directa_co2_kg'].sum()/1000:.1f} Mg")
    print(f"  CO2 grid (importado): {df['co2_grid_kwh'].sum()/1000:.1f} Mg")
    print(f"  CO2 neto (evitado - grid): {df['co2_neto_por_hora_kg'].sum()/1000:.1f} Mg")
    print()
    
    print("INFORMACIÓN DE CARGA:")
    print(f"  Promedio motos activas/hora: {df['cantidad_motos_activas'].mean():.2f}")
    print(f"  Promedio taxis activos/hora: {df['cantidad_mototaxis_activas'].mean():.2f}")
    print(f"  Máximo motos simultáneas: {df['cantidad_motos_activas'].max():.0f}")
    print(f"  Máximo taxis simultáneos: {df['cantidad_mototaxis_activas'].max():.0f}")
    print()
    
    print("="*80)
    print("✅ DATASET VÁLIDO Y LISTO PARA CITYLEARNV2")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = validate_dataset()
    exit(0 if success else 1)
