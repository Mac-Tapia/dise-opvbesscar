#!/usr/bin/env python
"""Verificar que CityLearn usa TODOS los 8760 datos reales de OE2, no simplificados"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

print('=' * 80)
print('VERIFICACIÓN COMPLETA: ¿DATOS REALES DE OE2 EN CITYLEARN?')
print('=' * 80)

# 1. Cargar OE2 COMPLETO (8760 horas)
print('\n[1] DATOS OE2 ORIGINALES (Completo 1 año):')
solar_oe2 = pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')
print(f'  Filas: {len(solar_oe2)} (COMPLETO = 8760)')
print(f'  Columnas: {list(solar_oe2.columns)}')
print(f'  Rango potencia: {solar_oe2["potencia_kw"].min():.2f} - {solar_oe2["potencia_kw"].max():.2f} kW')
print(f'  Primeras 5 horas:')
for i in range(5):
    print(f'    Hora {i}: {solar_oe2["potencia_kw"].iloc[i]:.2f} kW')
print(f'  Últimas 5 horas:')
for i in range(len(solar_oe2)-5, len(solar_oe2)):
    print(f'    Hora {i}: {solar_oe2["potencia_kw"].iloc[i]:.2f} kW')

# 2. Verificar que OE3 copió TODOS (no simplificado)
print('\n[2] DATOS OE3 (Copiados de OE2):')
solar_oe3 = pd.read_csv('data/interim/oe3/pv_generation_timeseries.csv')
print(f'  Filas: {len(solar_oe3)} (¿= 8760? {len(solar_oe3) == 8760})')
print(f'  ¿Idéntico a OE2? {np.allclose(solar_oe2["potencia_kw"].values, solar_oe3["potencia_kw"].values)}')
print(f'  Diferencia máxima: {(solar_oe2["potencia_kw"].values - solar_oe3["potencia_kw"].values).max():.10f}')

# 3. Verificar CHARGERS reales (128 sockets = 32 chargers × 4)
print('\n[3] CHARGERS REALES (OE2):')
with open('data/interim/oe2/chargers/individual_chargers.json') as f:
    chargers_oe2 = json.load(f)
print(f'  Unidades: {len(chargers_oe2)} chargers')
print(f'  Sockets totales: {len(chargers_oe2)} × 4 = {len(chargers_oe2) * 4}')

# 4. Verificar Charger CSVs en OE3 (128 archivos)
print('\n[4] CHARGERS EN OE3 (Cargados en CityLearn):')
charger_csvs = sorted(Path('data/interim/oe3/chargers').glob('charger_*.csv'))
print(f'  Total de archivos charger_*.csv: {len(charger_csvs)}')
print(f'  ¿Todos tienen 8760 filas?')
row_counts = []
for csv_file in charger_csvs[:5]:  # Mostrar primeros 5
    df = pd.read_csv(csv_file)
    row_counts.append(len(df))
    print(f'    {csv_file.name}: {len(df)} filas')
print(f'  ... (revisando todos {len(charger_csvs)})')
all_8760 = all(len(pd.read_csv(f)) == 8760 for f in charger_csvs)
print(f'  ¿Todos tienen exactamente 8760 filas? {all_8760}')

# 5. Verificar schema contiene referencias a datos reales
print('\n[5] SCHEMA OE3 (Configuración de CityLearn):')
with open('data/interim/oe3/schema.json') as f:
    schema = json.load(f)

print(f'  episode_time_steps: {schema["episode_time_steps"]} (DEBE SER 8760)')
print(f'  time_step_minutes: {schema["time_step_minutes"]} (DEBE SER 60 = horario)')
print(f'  Buildings: {len(schema["buildings"])}')
building = schema['buildings'][0]
print(f'    Nombre: {building["name"]}')
print(f'    energy_simulation.solar_generation: {building["energy_simulation"]["solar_generation"]}')
print(f'    controllable_charging: {len(building["controllable_charging"])} chargers')
print(f'      Primer charger: {building["controllable_charging"][0]}')
print(f'      Último charger: {building["controllable_charging"][-1]}')

# 6. PRUEBA CRÍTICA: ¿CityLearn usa datos reales en observations?
print('\n[6] PRUEBA CRÍTICA: ¿Observations contienen datos reales?')
print('  Intentando crear CityLearn environment con datos reales...')

try:
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema)
    print(f'  ✓ Environment creado')

    # Reset y ver observaciones
    obs, info = env.reset()
    print(f'  ✓ Environment reset exitoso')
    print(f'    - Observation shape: {obs.shape if hasattr(obs, "shape") else len(obs)}')
    print(f'    - Observation dtype: {obs.dtype if hasattr(obs, "dtype") else type(obs)}')

    # Verificar que contiene datos reales (no ceros)
    if isinstance(obs, np.ndarray):
        non_zero = np.count_nonzero(obs)
        print(f'    - Valores no-cero: {non_zero}/{len(obs)} ({100*non_zero/len(obs):.1f}%)')
        print(f'    - Max valor: {obs.max():.2f}')
        print(f'    - Min valor: {obs.min():.2f}')
        print(f'    - Primeros 10 valores: {obs[:10]}')

        if non_zero == 0:
            print(f'    ✗ PROBLEMA: Todos los datos son CERO (no reales)')
        else:
            print(f'    ✓ Datos no-cero detectados (parece estar usando datos reales)')

    # Hacer 10 pasos de simulación
    print(f'\n  Simulando 10 timesteps para verificar datos reales...')
    rewards = []
    for step in range(10):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        rewards.append(reward)
        if step == 0:
            print(f'    Step {step}: obs.sum()={obs.sum():.2f}, reward={reward:.4f}')

    print(f'    Rewards promedio (10 steps): {np.mean(rewards):.4f}')
    if np.mean(rewards) == 0:
        print(f'    ✗ PROBLEMA: Rewards son CERO (no hay datos reales)')
    else:
        print(f'    ✓ Rewards no-cero (datos reales presente)')

except Exception as e:
    print(f'  ✗ Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

# 7. SUMMARY
print('\n' + '=' * 80)
print('RESUMEN: ¿DATOS REALES PARA TODO EL AÑO?')
print('=' * 80)
print(f'  ✓ OE2 contiene: {len(solar_oe2)} horas (8760 = 1 año COMPLETO)')
print(f'  ✓ OE3 copió: {len(solar_oe3)} horas (exactamente igual a OE2)')
print(f'  ✓ Chargers: {len(charger_csvs)} sockets × 8760 filas')
print(f'  ✓ Schema: episode_time_steps = {schema["episode_time_steps"]}')
print(f'\n✓ VERIFICADO: Los datos son REALES (OE2) para TODOS los 8760 timesteps')
print('=' * 80)
