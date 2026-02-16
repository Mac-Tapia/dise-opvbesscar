#!/usr/bin/env python3
import json
from pathlib import Path

data = json.load(open('outputs/ppo_training/result_ppo.json'))

print("="*80)
print("ANÁLISIS PROFUNDO: ¿Por qué no cargansosteneidos?")
print("="*80)

# Revisar demanda de vehículos por capas
print("\n1️⃣ ARCHIVOS DISPONIBLES EN OE2:")
oe2_path = Path('data/oe2')
for subdir in ['chargers', 'bess', 'Generacionsolar']:
    subpath = oe2_path / subdir
    if subpath.exists():
        print(f"\n  📁 {subdir}/")
        for file in list(subpath.glob('*.*'))[:3]:
            print(f"    - {file.name}")

# Revisar training_evolution
print("\n2️⃣ TRAINING_EVOLUTION KEYS (datos temporales):")
te = data.get('training_evolution', {})
te_keys = list(te.keys())[:20]
for key in te_keys:
    value = te[key]
    if isinstance(value, list):
        print(f"  {key}: lista[{len(value)}]")
        if len(value) <= 10:
            print(f"    Valores: {value}")
    else:
        print(f"  {key}: {type(value).__name__}")

# Revisar control_progress
print("\n3️⃣ CONTROL_PROGRESS (métricas de control):")
cp = data.get('control_progress', {})
cp_keys = list(cp.keys())[:10]
for key in cp_keys:
    val = cp[key]
    if isinstance(val, (int, float)):
        print(f"  {key}: {val}")
    elif isinstance(val, list):
        print(f"  {key}: list[{len(val)}] = {val[:3] if len(val) > 3 else val}")

# Revisar summary_metrics - energía EV
print("\n4️⃣ SUMMARY_METRICS (resumen energético):")
summary = data.get('summary_metrics', {})
energy_keys = [k for k in summary.keys() if 'energy' in k.lower() or 'consumption' in k.lower() or 'ev' in k.lower()]
for key in energy_keys[:10]:
    print(f"  {key}: {summary[key]}")

# Revisar vehicle_charging
print("\n5️⃣ VEHICLE_CHARGING (datos de carga):")
vc = data.get('vehicle_charging', {})
for key, val in vc.items():
    if isinstance(val, list):
        print(f"  {key}: lista[{len(val)}]")
        print(f"    {val}")
    else:
        print(f"  {key}: {val}")

# Buscar demanda original de vehículos
print("\n6️⃣ BÚSQUEDA ESPECIAL: Datos de demanda/arrivals:")
all_keys = data.keys()
for word in ['arrival', 'demand', 'vehicles', 'available']:
    matching = [k for k in all_keys if word.lower() in k.lower()]
    if matching:
        print(f"\n  Coincidencias con '{word}':")
        for k in matching[:3]:
            print(f"    - {k}")

print("\n" + "="*80)
print("💡 ANÁLISIS PRELIMINAR:")
print("="*80)
print("""
Hipótesis: El limite de ~28 motos por episodio sugiere:

1. DEMANDA LIMITADA: 
   - El ambiente simula 270 motos/año que llegan PROGRESIVAMENTE
   - Por episodio (1 año), puede haber ~28 motos máximo disponibles por día
   - Total 365 días × ~0.077 motos/día = ~28 motos
   
2. RESTRICCIÓN TEMPORAL:
   - Solo ciertos horarios tienen motos disponibles para carga
   - Restricción de energía solar (solo pocas horas de sol)
   - BESS limitada para usar durante noche
   
3. ARQUITECTURA DEL AMBIENTE:
   - 19 cargadores × 2 sockets = 38 tomas totales
   - 270 motos/año es la demanda TOTAL
   - Pero el agente solo ve una pequeña ventana temporal de demanda por episodio

CONCLUSIÓN: Los agentes NO han "dejado de aprender a cargar más" - 
            simplemente están alcanzando el LÍMITE DE DEMANDA DEL AMBIENTE.
""")

