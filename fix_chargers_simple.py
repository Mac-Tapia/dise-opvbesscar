#!/usr/bin/env python3
"""
Generar CSVs simples para chargers que funcionen con CityLearn
"""
import pandas as pd
import numpy as np
from pathlib import Path

output_dir = Path("data/processed/citylearn/iquitos_ev_mall")
output_dir.mkdir(parents=True, exist_ok=True)

# Generar 128 archivos de chargers (8761 filas cada uno)
n_timesteps = 8760
for i in range(1, 129):
    charger_name = f"charger_{i}_1.csv"
    
    # Crear datos simples: estado de charger, EV ID, etc.
    # Horario de operación: 9:00 a 22:00 (13 horas)
    state = []
    for t in range(n_timesteps):
        hour_of_day = (t % 24)
        # Conectado si está entre 9 y 22, desconectado del resto
        if 9 <= hour_of_day < 22:
            state.append(1)  # Connected
        else:
            state.append(3)  # Commuting
    
    # Crear dataframe
    df = pd.DataFrame({
        "electric_vehicle_charger_state": state[:n_timesteps],
        "electric_vehicle_id": ["EV_001"] * n_timesteps,
        "electric_vehicle_departure_time": [np.nan if s == 3 else 1.0 for s in state[:n_timesteps]],
        "electric_vehicle_required_soc_departure": [np.nan if s == 3 else 90.0 for s in state[:n_timesteps]],
        "electric_vehicle_estimated_arrival_time": [np.nan if s == 1 else 1.0 for s in state[:n_timesteps]],
        "electric_vehicle_estimated_soc_arrival": [20.0] * n_timesteps,
    })
    
    # Agregar 1 fila extra para CityLearn (para acceso a t+1)
    last_row = df.iloc[-1:].copy()
    df = pd.concat([df, last_row], ignore_index=True)
    
    # Guardar
    df.to_csv(output_dir / charger_name, index=False)
    if i % 32 == 0:
        print(f"Generados {i} chargers...")

print(f"✓ Generados {128} archivos de chargers con {n_timesteps + 1} timesteps cada uno")
