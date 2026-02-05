#!/usr/bin/env python3
"""Generate BESS hourly dataset for CityLearn v2"""

import pandas as pd
from pathlib import Path
import numpy as np

# Crear directorio si no existe
Path('data/interim/oe2/bess').mkdir(parents=True, exist_ok=True)

# Crear timeseries BESS realista
dates = pd.date_range('2024-01-01', periods=8760, freq='h')
hours = dates.hour
dow = dates.dayofweek
month = dates.month

# Poder BESS (basado en carga/descarga típica del mall y EV)
# - Carga: durante horas solares (6-18)
# - Descarga: durante punta (18-22 y 6-9)
power_profile = np.zeros(8760)
for i, (h, d, m) in enumerate(zip(hours, dow, month)):
    if 6 <= h < 10:  # Mañana: descarga (peak evening residual)
        power_profile[i] = -200  # Inyecta 200 kW
    elif 10 <= h < 15:  # Mediodía: carga (PV disponible)
        power_profile[i] = 300  # Carga 300 kW
    elif 15 <= h < 18:  # Tarde: carga transitoria
        power_profile[i] = 150
    elif 18 <= h < 22:  # Noche: descarga (peak demand)
        power_profile[i] = -400  # Inyecta 400 kW
    # 22-6: sin operación (0 kW)

# Energía = Potencia × tiempo (1h)
energy_profile = power_profile.copy()

# SOC basado en integración de energía
soc = []
current_soc = 50  # Inicia en 50%
max_capacity = 4520
for e in energy_profile:
    current_soc += (e / max_capacity) * 100
    current_soc = max(0, min(100, current_soc))  # Clamp [0, 100]
    soc.append(current_soc)

# Crear DataFrame
df_bess = pd.DataFrame({
    'timestamp': dates,
    'power_kw': power_profile,
    'energy_kwh': energy_profile,
    'soc_percent': soc
})

# Guardar
output_path = Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv')
df_bess.to_csv(output_path, index=False)
print(f'Archivo BESS creado: {output_path}')
print(f'Filas: {len(df_bess)}')
print(f'Columnas: {list(df_bess.columns)}')
print(f'Potencia media: {df_bess["power_kw"].mean():.2f} kW')
print(f'SOC inicial: {df_bess["soc_percent"].iloc[0]:.1f}%')
print(f'SOC final: {df_bess["soc_percent"].iloc[-1]:.1f}%')
