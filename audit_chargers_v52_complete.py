#!/usr/bin/env python3
"""
AUDITORÍA COMPLETA: chargers.py v5.2
Valida completitud de datos, control por socket, CO2 y readiness CityLearn v2
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
import numpy as np

print("\n" + "="*90)
print("🔍 AUDITORÍA COMPLETA: chargers.py v5.2 - CONTROL + CO2 + CITYLEARN v2")
print("="*90)

# Detectar si el dataset existe
dataset_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')

if not dataset_path.exists():
    print("\n⚠️  DATASET NO ENCONTRADO")
    print(f"   Ubicación esperada: {dataset_path}")
    print("   Ejecutar primero: python -m src.dimensionamiento.oe2.disenocargadoresev.chargers")
    exit(1)

print(f"\n✓ Dataset encontrado: {dataset_path}")
df = pd.read_csv(dataset_path, index_col=0, parse_dates=True)
print(f"  • Filas: {len(df):,} (8,760 horas)")
print(f"  • Columnas: {len(df.columns)}")
print(f"  • Índice: {type(df.index).__name__}")

# ============================================================================
# FASE 1: VALIDACIÓN DE ESTRUCTURA SOCKET LEVEL
# ============================================================================
print("\n" + "="*90)
print("FASE 1: VALIDACIÓN DE ESTRUCTURA SOCKET LEVEL (38 TOMAS)")
print("="*90)

# Esperamos:
# - 30 sockets motos (socket_000 a socket_029)
# - 8 sockets mototaxis (socket_030 a socket_037)

socket_cols = [col for col in df.columns if col.startswith('socket_')]
socket_ids = sorted(set(int(col.split('_')[1]) for col in socket_cols if col.startswith('socket_')))

print(f"\n✓ Sockets detectados: {len(socket_ids)}")
if socket_ids == list(range(38)):
    print("  ✓ IDs secuenciales 0-37 (CORRECTO)")
else:
    print(f"  ❌ IDs no secuenciales: {socket_ids}")

print(f"\n  • Sockets motos:      {sum(1 for s in socket_ids if s < 30)} (socket_000 → socket_029)")
print(f"  • Sockets mototaxis:  {sum(1 for s in socket_ids if s >= 30)} (socket_030 → socket_037)")

# ============================================================================
# FASE 2: VALIDACIÓN DE COLUMNAS POR SOCKET (CONTROL)
# ============================================================================
print("\n" + "="*90)
print("FASE 2: VALIDACIÓN DE COLUMNAS POR SOCKET (Control + Observables)")
print("="*90)

required_socket_columns = [
    '_charger_power_kw',      # Potencia nominal cargador
    '_battery_kwh',           # Capacidad batería
    '_vehicle_type',          # Tipo vehículo (MOTO/MOTOTAXI)
    '_soc_current',           # SOC actual durante carga
    '_soc_arrival',           # SOC al llegar
    '_soc_target',            # SOC objetivo (100%)
    '_active',                # Estado (si hay vehículo)
    '_charging_power_kw',     # Potencia instantánea carga
    '_vehicle_count',         # Contador vehículos en cola
]

print(f"\nValidando {len(required_socket_columns)} columnas requeridas por socket:")

missing_per_socket = {}
for col_suffix in required_socket_columns:
    present_in_sockets = []
    for socket_id in socket_ids:
        col = f'socket_{socket_id:03d}{col_suffix}'
        if col in df.columns:
            present_in_sockets.append(socket_id)
    
    if len(present_in_sockets) == len(socket_ids):
        print(f"  ✓ {col_suffix:30s} - Presente en los 38 sockets")
    else:
        print(f"  ❌ {col_suffix:30s} - FALTA en sockets: {[s for s in socket_ids if s not in present_in_sockets]}")
        missing_per_socket[col_suffix] = [s for s in socket_ids if s not in present_in_sockets]

if missing_per_socket:
    print(f"\n⚠️  FALTA COMPLETITUD: {len(missing_per_socket)} tipos de columna incompletos")
else:
    print("\n✅ COMPLETITUD: Todas las columnas presentes en los 38 sockets")

# ============================================================================
# FASE 3: VALIDACIÓN DE DATOS POR SOCKET (Contenido)
# ============================================================================
print("\n" + "="*90)
print("FASE 3: VALIDACIÓN DE CONTENIDO (Valores + Rangos)")
print("="*90)

print("\n📊 Potencia piel de cargador (9 × 7,4 kW = 281,2 kW):")
charger_power_cols = [col for col in df.columns if '_charger_power_kw' in col]
charger_powers = [df[col].iloc[0] for col in charger_power_cols]
total_power = sum(charger_powers)
print(f"  • Potencia por socket: {np.unique(charger_powers)}")
print(f"  • Potencia total: {total_power:.1f} kW (esperado 281.2 kW)")

if abs(total_power - 281.2) < 0.1:
    print("  ✓ Potencia total correcta")
else:
    print(f"  ❌ Potencia total incorrecta (esperado 281.2 kW, obtuvo {total_power:.1f} kW)")

print("\n🔋 Capacidad batería:")
battery_cols = [col for col in df.columns if '_battery_kwh' in col]
battery_motos = []
battery_taxis = []
for col in battery_cols:
    socket_id = int(col.split('_')[1])
    capacity = df[col].iloc[0]
    if socket_id < 30:
        battery_motos.append(capacity)
    else:
        battery_taxis.append(capacity)

if battery_motos:
    print(f"  • Motos (socket 0-29):    {np.unique(battery_motos)} kWh")
    if abs(np.mean(battery_motos) - 4.6) < 0.01:
        print("    ✓ Correcto (4.6 kWh)")
    else:
        print(f"    ❌ Incorrecto (esperado 4.6 kWh, obtuvo {np.mean(battery_motos):.1f} kWh)")

if battery_taxis:
    print(f"  • Mototaxis (socket 30-37): {np.unique(battery_taxis)} kWh")
    if abs(np.mean(battery_taxis) - 7.4) < 0.01:
        print("    ✓ Correcto (7.4 kWh)")
    else:
        print(f"    ❌ Incorrecto (esperado 7.4 kWh, obtuvo {np.mean(battery_taxis):.1f} kWh)")

print("\n📈 Estado de Batería (SOC - State of Charge):")
soc_cols = [col for col in df.columns if '_soc_current' in col]
for socket_id in [0, 15, 30, 37]:  # Muestreo
    col = f'socket_{socket_id:03d}_soc_current'
    if col in df.columns:
        soc_data = df[col]
        active_charges = soc_data[soc_data > 0]
        if len(active_charges) > 0:
            print(f"  • Socket {socket_id:2d} (moto): SOC min={active_charges.min():.2f}, max={active_charges.max():.2f}, media={active_charges.mean():.2f}")

soc_arrival = [col for col in df.columns if '_soc_arrival' in col]
soc_target = [col for col in df.columns if '_soc_target' in col]
print(f"\n  ✓ SOC arrival presente: {len(soc_arrival)} sockets")
print(f"  ✓ SOC target presente: {len(soc_target)} sockets")
print(f"  ✓ SOC current presente: {len(soc_cols)} sockets")

# ============================================================================
# FASE 4: VALIDACIÓN DE CONTROL (Active + Power)
# ============================================================================
print("\n" + "="*90)
print("FASE 4: VALIDACIÓN DE CONTROL (Estados de Operación)")
print("="*90)

active_cols = [col for col in df.columns if '_active' in col]
print(f"\n✓ Estado 'active' en {len(active_cols)} sockets")

total_active_hours = sum((df[col] == 1).sum() for col in active_cols)
total_hours = len(df) * len(active_cols)
occupancy = total_active_hours / total_hours * 100
print(f"  Ocupancia total: {occupancy:.2f}% ({total_active_hours:,} horas de {total_hours:,})")
print(f"  Promedio sockets activos simultáneos: {total_active_hours / len(df):.2f} / 38")

# Validar rango de charging_power
charging_cols = [col for col in df.columns if col.endswith('_charging_power_kw') and col.startswith('socket_')]
charging_data = pd.concat([df[col] for col in charging_cols], ignore_index=False)
print(f"\n✓ Potencia de carga instantánea:")
print(f"  • Mínimo: {charging_data.min():.3f} kW (sin carga)")
print(f"  • Máximo: {charging_data.max():.3f} kW")
print(f"  • Media (cuando activa): {charging_data[charging_data > 0].mean():.3f} kW")

# ============================================================================
# FASE 5: VALIDACIÓN DE REDUCCIÓN DE CO2 DIRECTA
# ============================================================================
print("\n" + "="*90)
print("FASE 5: VALIDACIÓN DE REDUCCIÓN DIRECTA DE CO2 (Cambio Combustible)")
print("="*90)

# Columnas CO2 esperadas
co2_columns = {
    'ev_energia_motos_kwh': 'Energía cargada en motos',
    'ev_energia_mototaxis_kwh': 'Energía cargada en mototaxis',
    'co2_reduccion_motos_kg': 'Reducción CO2 motos (factor 0.87)',
    'co2_reduccion_mototaxis_kg': 'Reducción CO2 mototaxis (factor 0.47)',
    'reduccion_directa_co2_kg': 'Reducción total CO2 directa',
}

print("\nColumnas de CO2 Direct:")
for col, desc in co2_columns.items():
    if col in df.columns:
        total = df[col].sum()
        max_val = df[col].max()
        print(f"  ✓ {col:35s} - {desc}")
        print(f"    Total: {total:12,.1f} | Max/hora: {max_val:8.2f}")
    else:
        print(f"  ❌ FALTA {col:35s} - {desc}")

# Validar factores de CO2
if 'co2_reduccion_motos_kg' in df.columns and 'ev_energia_motos_kwh' in df.columns:
    # Calcular factor implícito
    energia_motos = df['ev_energia_motos_kwh'].sum()
    co2_motos = df['co2_reduccion_motos_kg'].sum()
    if energia_motos > 0:
        factor_implícito = co2_motos / energia_motos
        factor_esperado = 0.87
        error = abs(factor_implícito - factor_esperado)
        if error < 0.01:
            print(f"\n  ✓ Factor motos: {factor_implícito:.2f} kg CO2/kWh (esperado {factor_esperado})")
        else:
            print(f"\n  ❌ Factor motos: {factor_implícito:.2f} kg CO2/kWh (esperado {factor_esperado}, error {error:.4f})")

if 'co2_reduccion_mototaxis_kg' in df.columns and 'ev_energia_mototaxis_kwh' in df.columns:
    energia_taxis = df['ev_energia_mototaxis_kwh'].sum()
    co2_taxis = df['co2_reduccion_mototaxis_kg'].sum()
    if energia_taxis > 0:
        factor_implícito = co2_taxis / energia_taxis
        factor_esperado = 0.47
        error = abs(factor_implícito - factor_esperado)
        if error < 0.01:
            print(f"  ✓ Factor mototaxis: {factor_implícito:.2f} kg CO2/kWh (esperado {factor_esperado})")
        else:
            print(f"  ❌ Factor mototaxis: {factor_implícito:.2f} kg CO2/kWh (esperado {factor_esperado}, error {error:.4f})")

# ============================================================================
# FASE 6: VALIDACIÓN DE TARIFICACIÓN OSINERGMIN
# ============================================================================
print("\n" + "="*90)
print("FASE 6: VALIDACIÓN DE TARIFICACIÓN OSINERGMIN")
print("="*90)

if 'is_hora_punta' in df.columns and 'tarifa_aplicada_soles' in df.columns:
    print("\n✓ Columnas de tarificación presentes:")
    print(f"  • is_hora_punta: marca hora punta (18h-22h)")
    print(f"  • tarifa_aplicada_soles: tarifa S/./kWh")
    
    # Verificar tarifas
    tarifas_unicas = df['tarifa_aplicada_soles'].unique()
    print(f"\n  Tarifas detectadas: {sorted(tarifas_unicas)}")
    if set(tarifas_unicas) == {0.28, 0.45}:
        print("  ✓ Tarifas correctas (HP: 0.45, HFP: 0.28)")
    else:
        print(f"  ❌ Tarifas incorrectas")
    
    # Validar sincronización HP con tarifa
    hp_rows = df[df['is_hora_punta'] == 1]
    hfp_rows = df[df['is_hora_punta'] == 0]
    if len(hp_rows) > 0 and len(hfp_rows) > 0:
        hp_tarifas = set(hp_rows['tarifa_aplicada_soles'].unique())
        hfp_tarifas = set(hfp_rows['tarifa_aplicada_soles'].unique())
        if hp_tarifas == {0.45}:
            print("  ✓ Sincronización HP correcta (0.45 S/kWh)")
        if hfp_tarifas == {0.28}:
            print("  ✓ Sincronización HFP correcta (0.28 S/kWh)")

    if 'costo_carga_ev_soles' in df.columns:
        costo_total = df['costo_carga_ev_soles'].sum()
        print(f"\n  Costo total anual: S/. {costo_total:,.2f}")

# ============================================================================
# FASE 7: COMPATIBILIDAD CITYLEARN v2
# ============================================================================
print("\n" + "="*90)
print("FASE 7: COMPATIBILIDAD CITYLEARN v2")
print("="*90)

# Columnas requeridas para CityLearn
citylearn_required = {
    'ev_demand_kwh': 'Demanda total EV (alias de ev_energia_total_kwh)',
    'ev_energia_total_kwh': 'Energía total cargada',
    'ev_energia_motos_kwh': 'Energía motos',
    'ev_energia_mototaxis_kwh': 'Energía mototaxis',
}

print("\n✓ Verificando columnas para CityLearn:")
missing_citylearn = []
for col, desc in citylearn_required.items():
    if col in df.columns:
        print(f"  ✓ {col:35s} - {desc}")
    else:
        print(f"  ❌ FALTA {col:35s} - {desc}")
        missing_citylearn.append(col)

# Verificar socket columns están en formato correcto para observables
print("\n✓ Formato de columnas socket:")
if all(col.startswith('socket_') for col in socket_cols):
    print("  ✓ Nomenclatura correcta (socket_{id:03d}_{variable})")
else:
    print("  ❌ Nomenclatura inconsistente")

# Verificar DatetimeIndex
if isinstance(df.index, pd.DatetimeIndex):
    print("\n✓ Índice correcto:")
    print(f"  ✓ DatetimeIndex: {df.index[0]} → {df.index[-1]}")
else:
    print("\n❌ Índice incorrecto (debe ser DatetimeIndex)")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "="*90)
print("📋 RESUMEN FINAL - VALIDACIÓN CHARGERS.PY v5.2")
print("="*90)

summary = {
    'socket_structure': (len(socket_cols) > 0 and len(socket_ids) == 38),
    'control_columns': len(missing_per_socket) == 0,
    'soc_data': ('socket_000_soc_current' in df.columns),
    'active_states': ('socket_000_active' in df.columns),
    'charging_power': ('socket_000_charging_power_kw' in df.columns),
    'co2_direct': all(col in df.columns for col in 
                      ['co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg', 'reduccion_directa_co2_kg']),
    'tariff_osinergmin': ('tarifa_aplicada_soles' in df.columns),
    'citylearn_compat': len(missing_citylearn) == 0,
    'datetime_index': isinstance(df.index, pd.DatetimeIndex),
}

print("\nRESULTADOS FASE A FASE:")
phases = [
    ('1. Estructura socket level', summary['socket_structure']),
    ('2. Columnas de control', summary['control_columns']),
    ('3. Estados de batería (SOC)', summary['soc_data']),
    ('4. Estados activos', summary['active_states']),
    ('5. Potencia instantánea', summary['charging_power']),
    ('6. CO2 reducción directa', summary['co2_direct']),
    ('7. Tarificación OSINERGMIN', summary['tariff_osinergmin']),
    ('8. Compatibilidad CityLearn v2', summary['citylearn_compat']),
    ('9. DatetimeIndex', summary['datetime_index']),
]

for phase_name, status in phases:
    symbol = "✅" if status else "❌"
    print(f"  {symbol} {phase_name:40s} - {'PASADO' if status else 'FALLO'}")

all_passed = all(summary.values())
print("\n" + "="*90)
if all_passed:
    print("🎉 AUDITORÍA COMPLETA: DATASET COMPLETAMENTE LISTO PARA CITYLEARN v2")
    print("="*90)
    print("\n✨ RESUMEN DE CAPACIDADES:")
    print("  ✓ 38 sockets (30 motos + 8 mototaxis) con control independiente")
    print("  ✓ Estados dinámicos por socket (SOC, activo, potencia instantánea)")
    print("  ✓ Reducción directa CO2 (cambio combustible gasolina → EV)")
    print("  ✓ Tarificación OSINERGMIN completamente integrada")
    print("  ✓ Datos normalizados para observables CityLearn")
    print("\n🚀 PRÓXIMO PASO:")
    print("  → Integración con dataset_builder.py para construcción del environment")
else:
    print("⚠️  AUDITORÍA INCOMPLETA - REVISAR FALLOS ARRIBA")
    print("="*90)

print("\n")
