#!/usr/bin/env python3
"""Generate charger profiles from existing OE2 data"""

import pandas as pd
import json
import numpy as np
from pathlib import Path

print("Generando dataset de cargadores desde datos OE2 existentes...")
print()

# 1. Cargar datos existentes
print("[1] Cargando datos OE2 existentes...")

# Cargar especificaciones de cargadores
cargadores_path = Path('data/interim/oe2/chargers/individual_chargers.json')
with open(cargadores_path) as f:
    chargers_specs = json.load(f)
print(f"    OK: {len(chargers_specs)} cargadores cargados")

# Cargar demanda del mall (para patrones horarios realistas)
mall_demand_path = Path('data/interim/oe2/mall_demand_hourly.csv')
mall_demand = pd.read_csv(mall_demand_path)
print(f"    OK: Demanda del mall cargada ({len(mall_demand)} horas)")

# Cargar datos BESS (para referencia de ciclo de carga)
bess_path = Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv')
bess_data = pd.read_csv(bess_path)
print(f"    OK: Datos BESS cargados ({len(bess_data)} horas)")

print()
print("[2] Creando perfiles de carga de cargadores...")

# 2. Crear perfil de carga realista basado en demanda del mall
# Logica: cuando hay demanda de mall, hay demanda de carga de EVs
# Los cargadores operan 9-22 horas (13 horas/día)

# Normalizar demanda del mall para usarla como factor de carga disponible
demanda_norm = (mall_demand['demanda_kw'].values - mall_demand['demanda_kw'].min()) / \
               (mall_demand['demanda_kw'].max() - mall_demand['demanda_kw'].min())

# Crear 32 columnas (uno por cargador físico)
# Cada cargador tiene capacidad nominal de 7.36 kW (2912 motos + 416 mototaxis = 3328 vehículos)
# Total: 50 kW de demanda EV / 32 cargadores ≈ 1.56 kW por cargador
# Potencia nominal por cargador: ~2.3 kW

charger_data = {}
dates = pd.date_range('2024-01-01', periods=8760, freq='h')
hours = dates.hour

for charger_id in range(32):
    # Crear patrón basado en demanda del mall + hora del día
    power_profile = np.zeros(8760)

    for i, h in enumerate(hours):
        # Solo operan entre 9-22
        if 9 <= h <= 22:
            # Potencia base: entre 0.8 y 2.3 kW según demanda del mall
            base_power = 0.8 + (demanda_norm[i] * 1.5)

            # Patrón diario: pico al mediodía y tarde
            if 9 <= h < 12:
                daily_factor = 0.5 + (0.3 * (h - 9) / 3)  # Subida mañana
            elif 12 <= h < 15:
                daily_factor = 0.8 + (0.2 * np.sin((h - 12) * np.pi / 3))  # Pico mediodía
            elif 15 <= h < 18:
                daily_factor = 0.9 + (0.1 * np.sin((h - 15) * np.pi / 3))  # Pico tarde
            else:  # 18-22
                daily_factor = 0.7 + (0.3 * np.sin((h - 18) * np.pi / 4))  # Bajada noche

            power_profile[i] = base_power * daily_factor
        else:
            power_profile[i] = 0.0

    charger_data[f'Charger_{charger_id+1:02d}'] = power_profile

# Crear DataFrame
df_chargers = pd.DataFrame(charger_data)
df_chargers['timestamp'] = dates

print(f"    OK: 32 perfiles de cargadores creados")
print(f"    Potencia media por cargador: {df_chargers.drop('timestamp', axis=1).mean().mean():.2f} kW")
print(f"    Energía anual total: {df_chargers.drop('timestamp', axis=1).sum().sum():.0f} kWh")
print()

# 3. Guardar como chargers_hourly_profiles_annual.csv
output_path = Path('data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv')
df_chargers.to_csv(output_path, index=False)
print(f"[3] Guardado en: {output_path}")
print(f"    Filas: {len(df_chargers)}")
print(f"    Columnas: {df_chargers.shape[1]} (32 chargers + timestamp)")
print()

print("=" * 60)
print("OK: Dataset de cargadores generado desde datos OE2 existentes")
print("=" * 60)
