#!/usr/bin/env python3
"""Generate charger profiles for CityLearn v2"""

import pandas as pd
from pathlib import Path
import numpy as np

# Crear directorio si no existe
Path('data/interim/oe2/chargers').mkdir(parents=True, exist_ok=True)

# Crear perfil de carga de cargadores (horario diario que se repite)
# Operación: 9-22 (13 horas/día)
hours_24 = np.arange(24)

# Potencia por cargador (3.68 kW nominal dividido por 4 sockets ≈ 0.9 kW por socket)
# 128 sockets / 32 cargadores = 4 sockets/cargador
# Potencia total: ~272 kW para 128 sockets
# Potencia por socket: 272/128 ≈ 2.1 kW

# Crear perfil de demanda horaria
power_per_charger_kw = 2.1  # Per socket (realista para motos/mototaxis)

# Perfil de carga (% de utilización por hora)
# Pico al mediodía y tarde
usage_profile = np.array([
    0,     # 0: Sin operación
    0,     # 1
    0,     # 2
    0,     # 3
    0,     # 4
    0,     # 5
    0,     # 6
    0,     # 7
    0,     # 8
    0.3,   # 9: Inicio mañana
    0.5,   # 10
    0.7,   # 11
    0.8,   # 12: Pico mediodía
    0.75,  # 13
    0.7,   # 14
    0.65,  # 15
    0.8,   # 16
    0.9,   # 17: Pico tarde
    1.0,   # 18: Pico máximo
    0.95,  # 19
    0.85,  # 20
    0.6,   # 21: Bajada noche
    0.3,   # 22: Cierre
    0       # 23
])

# Crear timeseries anual expandiendo el perfil diario
dates = pd.date_range('2024-01-01', periods=8760, freq='h')
hours = dates.hour

# Crear datos de cargadores
charger_data = []
for h in hours:
    power = power_per_charger_kw * usage_profile[h]
    charger_data.append(power)

# Guardar como CSV legible
df_chargers = pd.DataFrame({
    'timestamp': dates,
    'hour': hours,
    'power_kw_per_socket': charger_data
})

# Guardar baseline para referencia
output_path = Path('data/interim/oe2/chargers/chargers_hourly_profiles.csv')
df_chargers.to_csv(output_path, index=False)
print(f'Archivo de perfil de cargadores creado: {output_path}')
print(f'Filas: {len(df_chargers)}')
print(f'Potencia media por socket: {df_chargers["power_kw_per_socket"].mean():.2f} kW')
print(f'Potencia máxima: {df_chargers["power_kw_per_socket"].max():.2f} kW')
print(f'Energía anual por socket: {df_chargers["power_kw_per_socket"].sum():.0f} kWh')
print(f'Energía anual total (128 sockets): {df_chargers["power_kw_per_socket"].sum() * 128:.0f} kWh')
