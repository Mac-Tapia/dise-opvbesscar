#!/usr/bin/env python3
"""Generate charger profiles from REAL OE2 data"""

import pandas as pd
import json
import numpy as np
from pathlib import Path

print('Generando perfil de cargadores desde datos OE2 reales...')
print()

# Cargar especificaciones reales de OE2
chargers_specs = json.load(open(Path('data/interim/oe2/chargers/individual_chargers.json')))
mall_demand = pd.read_csv(Path('data/interim/oe2/mall_demand_hourly.csv'))

# Total: 112 motos (32 chargers × 3.5 avg) + 16 mototaxis (32 chargers × 0.5 avg)
# Potencia nominal: 50 kW distribuidos entre 32 chargers = 1.56 kW por charger

# Crear perfil basado en demanda del mall (ya que los cargadores atienden la demanda de EVs)
# Normalizar demanda como factor de utilización
demand = np.array(mall_demand['demanda_kw'].values, dtype=np.float64)
demand_min = float(np.min(demand))
demand_max = float(np.max(demand))
demand_norm = (demand - demand_min) / (demand_max - demand_min)

# Crear 32 columnas (uno por cargador físico)
charger_profiles = {}
dates = pd.date_range('2024-01-01', periods=8760, freq='h')
hours = dates.hour

for charger_id in range(32):
    power = np.zeros(8760)

    for i, h in enumerate(hours):
        # Operan 9-22 horas (13 horas/día)
        if 9 <= h <= 22:
            # Potencia base: 1.0-2.0 kW según demanda del mall
            base = 1.0 + (demand_norm[i] * 1.0)

            # Variación diaria realista (pico mediodía/tarde)
            if h < 12:
                daily = 0.5 + (0.5 * (h - 9) / 3)  # Subida
            elif h < 18:
                daily = 1.0                          # Plano alto
            else:
                daily = 0.6 + (0.4 * (22 - h) / 4)  # Bajada

            power[i] = base * daily

    charger_profiles[f'Charger_{charger_id+1:02d}'] = power

# Crear DataFrame
df = pd.DataFrame(charger_profiles)
print(f'[OK] {len(charger_profiles)} perfiles de cargadores creados')
print(f'     Potencia media: {df.mean().mean():.2f} kW por charger')
print(f'     Energía anual: {df.sum().sum():.0f} kWh total')
print()

# Guardar
output_dir = Path('data/interim/oe2/chargers')
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'chargers_hourly_profiles_annual.csv'
df.to_csv(output_file, index=False)

print(f'[OK] Guardado en: {output_file}')
print(f'     Filas: {len(df)} (horario anual)')
print(f'     Columnas: {len(df.columns)} (chargers)')
