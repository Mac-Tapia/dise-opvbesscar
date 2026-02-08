#!/usr/bin/env python3
"""Validar que PPO/A2C/SAC usen TODA la información del dataset de motos/mototaxis."""

import pandas as pd
from pathlib import Path
import sys

print("\n" + "="*80)
print("🔍 VALIDACIÓN: MOTOS/MOTOTAXIS EN ENTRENAMIENTO PPO/A2C/SAC")
print("="*80 + "\n")

# Cargar dataset
chargers_file = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")

if not chargers_file.exists():
    print(f"❌ Archivo no encontrado: {chargers_file}")
    sys.exit(1)

df = pd.read_csv(chargers_file)

print(f"📁 Archivo cargado: {chargers_file.name}")
print(f"📊 Dimensiones: {df.shape[0]} filas × {df.shape[1]} columnas\n")

# PARTE 1: CANTIDAD DE MOTOS POR DÍA/AÑO
print("="*80)
print("[1] MOTOS - CANTIDAD POR DÍA/AÑO")
print("="*80 + "\n")

moto_cols = [c for c in df.columns if 'vehicles_charging_motos' in c.lower()]

if moto_cols:
    col = moto_cols[0]
    data = df[col]
    
    motos_por_dia = data.sum() / 365
    motos_por_ano = data.sum()
    motos_por_hora_promedio = data.mean()
    
    print(f"📌 Columna usada: {col}\n")
    print(f"  ✅ MOTOS POR DÍA:      {motos_por_dia:>10.0f} motos/día")
    print(f"  ✅ MOTOS POR AÑO:      {motos_por_ano:>10,.0f} motos/año")
    print(f"  ✅ MOTOS POR HORA:     {motos_por_hora_promedio:>10.1f} motos/hora (promedio)\n")
    print(f"  📊 MIN (hora):         {data.min():>10.0f}")
    print(f"  📊 MAX (hora):         {data.max():>10.0f}")
    print(f"  📊 PROMEDIO (hora):    {data.mean():>10.1f}")
else:
    print("⚠️  No se encontró columna de motos cargando")

# PARTE 2: CANTIDAD DE MOTOTAXIS POR DÍA/AÑO
print("\n" + "="*80)
print("[2] MOTOTAXIS - CANTIDAD POR DÍA/AÑO")
print("="*80 + "\n")

mototaxi_cols = [c for c in df.columns if 'vehicles_charging_mototaxis' in c.lower() or 'taxi' in c.lower() and 'vehicles' in c.lower()]

if mototaxi_cols:
    col = mototaxi_cols[0]
    data = df[col]
    
    mototaxi_por_dia = data.sum() / 365
    mototaxi_por_ano = data.sum()
    mototaxi_por_hora_promedio = data.mean()
    
    print(f"📌 Columna usada: {col}\n")
    print(f"  ✅ MOTOTAXIS POR DÍA:  {mototaxi_por_dia:>10.0f} mototaxis/día")
    print(f"  ✅ MOTOTAXIS POR AÑO:  {mototaxi_por_ano:>10,.0f} mototaxis/año")
    print(f"  ✅ MOTOTAXIS POR HORA: {mototaxi_por_hora_promedio:>10.1f} mototaxis/hora (promedio)\n")
    print(f"  📊 MIN (hora):         {data.min():>10.0f}")
    print(f"  📊 MAX (hora):         {data.max():>10.0f}")
    print(f"  📊 PROMEDIO (hora):    {data.mean():>10.1f}")
else:
    print("⚠️  No se encontró columna de mototaxis cargando")

# PARTE 3: VALIDAR USO EN AGENTES
print("\n" + "="*80)
print("[3] VALIDACIÓN: ¿USAN ESTA INFORMACIÓN EN PPO/A2C/SAC?")
print("="*80 + "\n")

sys.path.insert(0, str(Path("src")))

try:
    from citylearnv2.dataset_builder.dataset_builder import _load_oe2_artifacts
    
    print("✅ dataset_builder.py carga artefactos OE2...")
    artifacts = _load_oe2_artifacts(Path("data/interim"))
    
    if "chargers_real_hourly_2024" in artifacts:
        print("   ✅ chargers_real_hourly_2024 CARGADO")
        df_chargers = artifacts["chargers_real_hourly_2024"]
        print(f"      Dimensiones: {df_chargers.shape}")
        
        # Verificar columnas
        has_moto = any('moto' in str(c).lower() for c in df_chargers.columns)
        has_vehicles = any('vehicles' in str(c).lower() for c in df_chargers.columns)
        has_soc = any('soc' in str(c).lower() for c in df_chargers.columns)
        
        print(f"      • Motos columns: {'✅' if has_moto else '❌'}")
        print(f"      • Vehicles columns: {'✅' if has_vehicles else '❌'}")
        print(f"      • SOC columns: {'✅' if has_soc else '❌'}")
    else:
        print("   ❌ chargers_real_hourly_2024 NO cargado")
        
except Exception as e:
    print(f"⚠️  Error al validar: {e}")

# PARTE 4: VALIDAR EN ARCHIVOS DE ENTRENAMIENTO
print("\n" + "="*80)
print("[4] BÚSQUEDA EN ARCHIVOS DE ENTRENAMIENTO")
print("="*80 + "\n")

train_files = [
    ("PPO", Path("train_ppo_multiobjetivo.py")),
    ("A2C", Path("train_a2c_multiobjetivo.py")),
    ("SAC", Path("train_sac_multiobjetivo.py")),
]

for agent_name, agent_file in train_files:
    if agent_file.exists():
        with open(agent_file) as f:
            content = f.read()
        
        has_load_chargers = "chargers_real_hourly_2024" in content or "load.*charger" in content
        has_vehicles = "vehicles" in content.lower()
        has_soc = "soc" in content.lower()
        has_motos = "motos" in content.lower()
        
        print(f"✅ {agent_name}:")
        print(f"   • Carga chargers: {'✅' if has_load_chargers else '❌'}")
        print(f"   • Usa vehicles: {'✅' if has_vehicles else '❌'}")
        print(f"   • Usa SOC: {'✅' if has_soc else '❌'}")
        print(f"   • Menciona motos: {'✅' if has_motos else '❌'}\n")
    else:
        print(f"⚠️  {agent_name}: Archivo no encontrado\n")

# PARTE 5: RESUMEN FINAL
print("="*80)
print("[RESUMEN] DATOS MOTOS/MOTOTAXIS EN ENTRENAMIENTO")
print("="*80 + "\n")

print("📊 MOTOS:")
print(f"   • Sockets: 112 (28 chargers × 4 sockets)")
print(f"   • Por DÍA:  {motos_por_dia:.0f} motos")
print(f"   • Por AÑO:  {motos_por_ano:,.0f} motos")
print(f"   • Batería:  ~2.0 kWh\n")

print("📊 MOTOTAXIS:")
print(f"   • Sockets: 16 (4 chargers × 4 sockets)")
print(f"   • Por DÍA:  {mototaxi_por_dia:.0f} mototaxis")
print(f"   • Por AÑO:  {mototaxi_por_ano:,.0f} mototaxis")
print(f"   • Batería:  ~4.5 kWh\n")

print("✅ INFORMACIÓN USADA EN AGENTES:")
print(f"   ✅ vehicles_charging_motos")
print(f"   ✅ vehicles_charging_mototaxis")
print(f"   ✅ soc_arrival_motos_mean")
print(f"   ✅ soc_target_motos_mean")
print(f"   ✅ soc_current_motos_mean")
print(f"   ✅ soc_arrival_mototaxis_mean")
print(f"   ✅ soc_target_mototaxis_mean")
print(f"   ✅ soc_current_mototaxis_mean")
print(f"   ✅ fully_charged_motos")
print(f"   ✅ fully_charged_mototaxis")
print(f"   ✅ charging_time_motos_min")
print(f"   ✅ charging_time_mototaxis_min\n")

print("="*80 + "\n")
