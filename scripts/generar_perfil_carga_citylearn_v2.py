#!/usr/bin/env python3
"""
GENERADOR DE PERFIL DE CARGA - CITYLEARN V2
=============================================
Genera un perfil de carga completo para entrenar con CityLearn v2 durante un año.

Integra:
- Demanda real del Mall Dos Playas (building_load.csv: 8,760 timesteps)
- Generación solar real Iquitos (pv_generation_timeseries.csv: 8,760 timesteps)
- Demanda dinámmica de EV (32 cargadores, 128 tomas)
- Parámetros BESS reales (1,711.6 kWh / 622.4 kW)

Salida: Archivos CSV listos para CityLearn v2
"""

import csv
import json
from pathlib import Path
from datetime import datetime, timedelta

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT = SCRIPT_DIR.parent.absolute()
OE2_DIR = ROOT / "data" / "oe2"
CITYLEARN_DIR = OE2_DIR / "citylearn"
OUTPUT_DIR = CITYLEARN_DIR / "training_data"

print("=" * 90)
print("🎮 GENERADOR DE PERFIL DE CARGA - CITYLEARN V2")
print("=" * 90)
print()

# ============================================================================
# 1. CARGAR DATOS REALES
# ============================================================================

print("📥 Cargando datos reales de Iquitos...")
print()

# Cargar demanda del Mall
building_load_file = CITYLEARN_DIR / "building_load.csv"
print(f"  ☀️  Building Load (Mall): {building_load_file.name}")

mall_demand = []
with open(building_load_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        mall_demand.append(float(row['non_shiftable_load']))

print(f"     → {len(mall_demand)} timesteps (1 año)")
print(f"     → Mín: {min(mall_demand):.2f} kWh, Máx: {max(mall_demand):.2f} kWh")
print(f"     → Promedio: {sum(mall_demand)/len(mall_demand):.2f} kWh/hora")

# Cargar generación solar
pv_file = OE2_DIR / "pv_generation_timeseries.csv"
print(f"\n  ☀️  PV Generation: {pv_file.name}")

pv_generation = []
with open(pv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Detectar columna de generación
        val = row.get('Solar_Generation_kWh') or row.get('power_output_kw') or row.get('pv_kwh')
        if val:
            pv_generation.append(float(val))

print(f"     → {len(pv_generation)} timesteps (1 año)")
print(f"     → Mín: {min(pv_generation):.2f} kW, Máx: {max(pv_generation):.2f} kW")
print(f"     → Promedio: {sum(pv_generation)/len(pv_generation):.2f} kW/hora")

# Cargar parámetros BESS
bess_file = OE2_DIR / "bess_dimensionamiento_schema.json"
print(f"\n  🔋 BESS Schema: {bess_file.name}")

with open(bess_file, 'r') as f:
    bess_schema = json.load(f)

capacity = bess_schema.get('capacity_kwh', 1711.6)
power = bess_schema.get('power_kw', 622.4)
dod = bess_schema.get('dod', 0.80)
efficiency = bess_schema.get('efficiency', 0.95)

print(f"     → Capacidad: {capacity:.2f} kWh")
print(f"     → Potencia: {power:.2f} kW")
print(f"     → DoD: {dod*100:.0f}%")
print(f"     → Eficiencia: {efficiency*100:.0f}%")

# Cargar parámetros EV
ev_file = OE2_DIR / "tabla_escenarios_vehiculos.csv"
print(f"\n  🚗 EV Scenario: {ev_file.name}")

with open(ev_file, 'r', encoding='utf-8', errors='ignore') as f:
    f.readline()  # skip header
    for line in f:
        parts = line.strip().split(',')
        if 'RECOMENDADO' in line:
            print(f"     → Escenario: RECOMENDADO")
            print(f"     → Cargadores: {parts[1]}")
            print(f"     → Sockets: {parts[2]}")
            print(f"     → Demanda/día: {parts[3]} kWh")
            break

# ============================================================================
# 2. GENERAR PERFIL DE CARGA EV DINÁMICO
# ============================================================================

print("\n" + "=" * 90)
print("🔧 Generando perfil de carga EV dinámico...")
print("=" * 90)
print()

# Perfil horario de demanda EV (32 cargadores, patrón típico)
# Basado en tabla_escenarios_vehiculos.csv - 2,823 kWh/día
ev_profile_24h = [
    50,    # 00:00 - Noche (carga lenta)
    40,    # 01:00
    30,    # 02:00
    30,    # 03:00
    30,    # 04:00
    50,    # 05:00 - Apertura matinal
    100,   # 06:00
    180,   # 07:00 - Aumento por llegadas
    250,   # 08:00 - Pico matinal
    280,   # 09:00
    280,   # 10:00
    250,   # 11:00 - Antes almuerzo
    200,   # 12:00 - Almuerzo (reducción)
    180,   # 13:00
    200,   # 14:00 - Después almuerzo
    220,   # 15:00
    250,   # 16:00 - Tarde alta
    280,   # 17:00 - Pico tarde
    250,   # 18:00
    200,   # 19:00 - Disminución
    150,   # 20:00
    100,   # 21:00 - Cierre
    80,    # 22:00
    60,    # 23:00
]

# Normalizar a 2,823 kWh/día
ev_daily_target = 2823
ev_profile_sum = sum(ev_profile_24h)
ev_profile_24h = [x * (ev_daily_target / ev_profile_sum) for x in ev_profile_24h]

print(f"  Perfil EV generado:")
print(f"     → 24 horas con patrones realistas")
print(f"     → Picos: mañana (08:00-10:00) y tarde (16:00-18:00)")
print(f"     → Mínimos: noche (00:00-05:00)")
print(f"     → Total diario: {sum(ev_profile_24h):.2f} kWh")

# Expandir a 8,760 timesteps (365 días)
ev_generation = []
for day in range(365):
    for hour in range(24):
        ev_generation.append(ev_profile_24h[hour])

# Agregar 2 horas extra si es necesario
while len(ev_generation) < len(mall_demand):
    ev_generation.append(ev_profile_24h[0])

print(f"  Expandido a 8,760 timesteps ✅")

# ============================================================================
# 3. CREAR DIRECTORIO DE SALIDA
# ============================================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"\n✅ Directorio de salida: {OUTPUT_DIR}")

# ============================================================================
# 4. GENERAR ARCHIVOS CSV PARA CITYLEARN V2
# ============================================================================

print("\n" + "=" * 90)
print("💾 Generando archivos CSV para CityLearn v2...")
print("=" * 90)
print()

# Archivo 1: Demanda total (Mall + EV)
print("  1️⃣  Generando: demand_profile.csv")
demand_file = OUTPUT_DIR / "demand_profile.csv"
with open(demand_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Hour', 'Mall_Load_kWh', 'EV_Demand_kWh', 'Total_Demand_kWh'])

    for hour in range(len(mall_demand)):
        total = mall_demand[hour] + ev_generation[hour]
        writer.writerow([
            hour,
            f"{mall_demand[hour]:.2f}",
            f"{ev_generation[hour]:.2f}",
            f"{total:.2f}"
        ])

total_demand = sum(mall_demand) + sum(ev_generation)
print(f"     ✅ {len(mall_demand)} timesteps")
print(f"     ✅ Demanda anual: {total_demand:,.0f} kWh")

# Archivo 2: Generación Solar
print("\n  2️⃣  Generando: solar_generation_profile.csv")
solar_file = OUTPUT_DIR / "solar_generation_profile.csv"
with open(solar_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Hour', 'PV_Generation_kW'])

    for hour in range(len(pv_generation)):
        writer.writerow([hour, f"{pv_generation[hour]:.2f}"])

total_solar = sum(pv_generation)
print(f"     ✅ {len(pv_generation)} timesteps")
print(f"     ✅ Generación anual: {total_solar:,.0f} kWh")

# Archivo 3: Balance energético
print("\n  3️⃣  Generando: energy_balance_profile.csv")
balance_file = OUTPUT_DIR / "energy_balance_profile.csv"
with open(balance_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Hour',
        'PV_Generation_kWh',
        'Total_Demand_kWh',
        'Solar_Surplus_Deficit_kWh',
        'PV_Coverage_Percent'
    ])

    for hour in range(len(pv_generation)):
        demand = mall_demand[hour] + ev_generation[hour]
        surplus_deficit = pv_generation[hour] - demand
        coverage = (pv_generation[hour] / max(demand, 0.01)) * 100

        writer.writerow([
            hour,
            f"{pv_generation[hour]:.2f}",
            f"{demand:.2f}",
            f"{surplus_deficit:.2f}",
            f"{coverage:.2f}"
        ])

# Archivo 4: Parámetros BESS
print("\n  4️⃣  Generando: bess_parameters.csv")
bess_params_file = OUTPUT_DIR / "bess_parameters.csv"
with open(bess_params_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Parameter', 'Value', 'Unit', 'Description'])
    writer.writerow(['Capacity', f"{capacity:.2f}", 'kWh', 'Usable energy capacity'])
    writer.writerow(['Nominal_Power', f"{power:.2f}", 'kW', 'Charge/discharge power'])
    writer.writerow(['DoD', f"{dod*100:.0f}", '%', 'Depth of Discharge'])
    writer.writerow(['Efficiency_Roundtrip', f"{efficiency*100:.0f}", '%', 'Round-trip efficiency'])
    writer.writerow(['C_Rate', f"{power/capacity:.2f}", 'C', 'Power to capacity ratio'])
    writer.writerow(['Initial_SOC', '50', '%', 'Starting state of charge'])
    writer.writerow(['Min_SOC', f"{(1-dod)*100:.0f}", '%', 'Minimum SOC'])
    writer.writerow(['Max_SOC', '100', '%', 'Maximum SOC'])

print(f"     ✅ 8 parámetros configurados")

# Archivo 5: Configuración CityLearn v2
print("\n  5️⃣  Generando: citylearn_config.json")
citylearn_config = {
    "schema_version": "v2",
    "simulation": {
        "timestep_duration_seconds": 3600,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "total_timesteps": 8760,
        "frequency": "hourly"
    },
    "building": {
        "name": "Mall Dos Playas",
        "location": {
            "city": "Iquitos",
            "state": "Loreto",
            "country": "Peru",
            "latitude": -3.7492,
            "longitude": -73.2345,
            "timezone": "America/Lima",
            "altitude": 106
        }
    },
    "electrical_loads": {
        "mall_load": {
            "data_file": "demand_profile.csv",
            "column": "Mall_Load_kWh",
            "description": "Non-shiftable load (Mall Dos Playas)"
        },
        "ev_charging": {
            "data_file": "demand_profile.csv",
            "column": "EV_Demand_kWh",
            "description": "Electric vehicle charging demand (32 chargers)"
        }
    },
    "renewable_energy": {
        "photovoltaic": {
            "data_file": "solar_generation_profile.csv",
            "column": "PV_Generation_kW",
            "nominal_power": 3000,
            "capacity": 3000,
            "technology": "Monocrystalline"
        }
    },
    "electrical_storage": {
        "battery": {
            "data_file": "bess_parameters.csv",
            "type": "Lithium-ion",
            "capacity_kwh": capacity,
            "nominal_power_kw": power,
            "dod_percent": dod * 100,
            "efficiency_roundtrip": efficiency,
            "initial_soc_percent": 50
        }
    },
    "grid": {
        "grid_import": {
            "available": True,
            "dynamic_pricing": False
        },
        "grid_export": {
            "available": True,
            "export_rate_method": "net_metering"
        }
    },
    "control_objectives": [
        "minimize_grid_imports",
        "maximize_self_consumption",
        "maintain_battery_health",
        "ensure_ev_charging"
    ]
}

config_file = OUTPUT_DIR / "citylearn_config.json"
with open(config_file, 'w') as f:
    json.dump(citylearn_config, f, indent=2)

print(f"     ✅ Configuración CityLearn v2 generada")

# ============================================================================
# 5. GENERAR RESUMEN ESTADÍSTICO
# ============================================================================

print("\n" + "=" * 90)
print("📊 RESUMEN ESTADÍSTICO DEL PERFIL DE CARGA")
print("=" * 90)
print()

# Calcular estadísticas
mall_daily = sum(mall_demand) / 365
ev_daily = sum(ev_generation) / 365
total_daily = mall_daily + ev_daily
solar_daily = sum(pv_generation) / 365

print("🏢 DEMANDA MALL (REAL):")
print(f"   • Diaria: {mall_daily:,.0f} kWh")
print(f"   • Anual: {sum(mall_demand):,.0f} kWh")
print(f"   • Porcentaje: {(sum(mall_demand)/(sum(mall_demand)+sum(ev_generation))*100):.1f}%")

print("\n🚗 DEMANDA EV (DINÁMICO):")
print(f"   • Diaria: {ev_daily:,.0f} kWh")
print(f"   • Anual: {sum(ev_generation):,.0f} kWh")
print(f"   • Porcentaje: {(sum(ev_generation)/(sum(mall_demand)+sum(ev_generation))*100):.1f}%")

print("\n⚡ DEMANDA TOTAL:")
print(f"   • Diaria: {total_daily:,.0f} kWh")
print(f"   • Anual: {total_demand:,.0f} kWh")

print("\n☀️  GENERACIÓN SOLAR:")
print(f"   • Diaria: {solar_daily:,.0f} kWh")
print(f"   • Anual: {sum(pv_generation):,.0f} kWh")

solar_coverage = (sum(pv_generation) / total_demand) * 100
print(f"   • Cobertura solar: {solar_coverage:.1f}%")

deficit_kwh = max(0, total_demand - sum(pv_generation))
surplus_kwh = max(0, sum(pv_generation) - total_demand)

print("\n📈 BALANCE ENERGÉTICO ANUAL:")
print(f"   • Superávit solar: {surplus_kwh:,.0f} kWh")
print(f"   • Déficit solar: {deficit_kwh:,.0f} kWh")
print(f"   • Necesidad de almacenamiento: {deficit_kwh/365:.0f} kWh/día (promedio)")

print("\n🔋 BESS DIMENSIONADO:")
print(f"   • Capacidad: {capacity:.0f} kWh")
print(f"   • Potencia: {power:.0f} kW")
print(f"   • Relación C-rate: {power/capacity:.2f}C")
print(f"   • Ciclaje máximo/día: {(deficit_kwh/365)/capacity:.2f} ciclos")

print("\n" + "=" * 90)
print("✅ PERFIL DE CARGA GENERADO EXITOSAMENTE")
print("=" * 90)
print()

print("📁 ARCHIVOS GENERADOS EN:", OUTPUT_DIR)
print()
print("   1. demand_profile.csv")
print("      → Demanda horaria (Mall + EV) para todo el año")
print()
print("   2. solar_generation_profile.csv")
print("      → Generación solar Iquitos (datos reales)")
print()
print("   3. energy_balance_profile.csv")
print("      → Balance energético horario (PV vs Demanda)")
print()
print("   4. bess_parameters.csv")
print("      → Parámetros del BESS (1,711.6 kWh / 622.4 kW)")
print()
print("   5. citylearn_config.json")
print("      → Configuración completa CityLearn v2")
print()

print("🎮 LISTO PARA ENTRENAR CON CITYLEARN V2")
print()
print("   Próximo paso:")
print("   $ python -m src.iquitos_citylearn.oe2.train_citylearn_v2 \\")
print(f"       --config {config_file}")
print()

# ============================================================================
# 6. CREAR SCRIPT DE ENTRENAMIENTO
# ============================================================================

training_script = OUTPUT_DIR / "run_training.sh"
with open(training_script, 'w', encoding='utf-8') as f:
    f.write(f"""#!/bin/bash
# Script para entrenar con CityLearn v2

cd {ROOT}

python -m src.iquitos_citylearn.oe2.train_citylearn_v2 \\
    --config {config_file} \\
    --episodes 50 \\
    --device cuda \\
    --output-dir ./checkpoints/citylearn_v2/

echo "Training completed"
""")

print(f"Training script: {training_script}")
