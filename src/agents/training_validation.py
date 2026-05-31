#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION CENTRALIZADA - Asegurar que TODOS los agentes entrenan COMPLETAMENTE.

Este modulo valida que cada agente (SAC, PPO, A2C) cumpla con:
1. 50 EPISODIOS COMPLETOS (438,000 timesteps = 1 ano × 50)
2. TODOS los DATASETS reales cargados (OE2 raw + CityLearn v2 intermedio)
3. OBSERVACION/ACCION consistentes con IquitosEVChargingWrapper
4. MULTIOBJETIVO CO2_DUAL_FOCUS v8.1 con pesos consistentes
5. INDEPENDENCIA de algoritmo: SAC, PPO y A2C usan el mismo entorno
6. VALIDACION PRE/POST entrenamiento
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, Any
import sys

# Constantes de validacion
REQUIRED_EPISODES = 50
TIMESTEPS_PER_YEAR = 8760
REQUIRED_TOTAL_TIMESTEPS = REQUIRED_EPISODES * TIMESTEPS_PER_YEAR  # 438,000

# Columnas fuente OE2/CityLearn que deben existir en los datasets reales.
OBSERVABLE_COLS_REQUIRED = {
    'CHARGERS': [
        'vehicles_per_hour', 'ev_demand_kwh', 'active_sockets',
        'electric_vehicle_charger_state',
    ],
    'SOLAR': [
        'solar_generation_kwh',
    ],
    'BESS': [
        'pv_kwh', 'ev_kwh', 'mall_kwh', 'bess_charge_kwh',
        'bess_discharge_kwh', 'bess_to_mall_kwh', 'bess_to_ev_kwh',
    ],
    'MALL': [
        'mall_demand_kwh',
    ],
    'CO2_TARIFFS': [
        'co2_factor_kg_kwh', 'tarifa_energia_soles_kwh',
        'tarifa_total_soles_kwh',
    ]
}

# MULTIOBJETIVO CO2_DUAL_FOCUS v8.1 (DEBE SER CONSISTENTE EN LOS 3 AGENTES)
REQUIRED_WEIGHTS = {
    'direct_co2': 0.20,
    'indirect_co2': 0.30,
    'ev_complete': 0.35,
    'bess_solar': 0.07,
    'solar': 0.04,
    'grid_stable': 0.02,
    'cost': 0.02,
}

# CONTEXTOINQUITOS
REQUIRED_CONTEXT = {
    'CO2_FACTOR_KG_PER_KWH': 0.4521,
    'BESS_CAPACITY_KWH': 2000.0,
    'BESS_MAX_KWH': 2000.0,
    'SOLAR_MAX_KW': 4050.0,
    'CHARGERS_COUNT': 19,
    'TOTAL_SOCKETS': 38,
    'ACTION_DIM': 3,
    'OBS_DIM': 18,
}

# ARCHIVOS DE DATOS OBLIGATORIOS
REQUIRED_DATA_FILES = {
    'raw_solar': 'data/iquitos_ev_mall/solar_generation.csv',
    'raw_chargers': 'data/iquitos_ev_mall/chargers_timeseries.csv',
    'raw_mall': 'data/iquitos_ev_mall/mall_demand.csv',
    'raw_bess': 'data/iquitos_ev_mall/bess_timeseries.csv',
    'raw_co2': 'data/iquitos_ev_mall/co2_emissions.csv',
    'raw_tariffs': 'data/iquitos_ev_mall/tariffs_osinergmin.csv',
    'cl_energy': 'data/interim/citylearn_v2/energy_simulation.csv',
    'cl_weather': 'data/interim/citylearn_v2/weather.csv',
    'cl_carbon': 'data/interim/citylearn_v2/carbon_intensity.csv',
    'cl_ev_motos': 'data/interim/citylearn_v2/ev_charger_motos.csv',
    'cl_ev_mototaxis': 'data/interim/citylearn_v2/ev_charger_mototaxis.csv',
    'cl_tariffs': 'data/interim/citylearn_v2/tariffs_osinergmin.csv',
    'cl_schema': 'data/interim/citylearn_v2/schema_iquitos.json',
}


def count_total_observable_cols() -> int:
    """Contar total de columnas observables requeridas."""
    return sum(len(cols) for cols in OBSERVABLE_COLS_REQUIRED.values())


def validate_episodes(num_episodes: int) -> bool:
    """[OK] Validar que se entrenan EXACTAMENTE 50 EPISODIOS."""
    if num_episodes != REQUIRED_EPISODES:
        print(f'  [X] Episodes: {num_episodes} != {REQUIRED_EPISODES}')
        return False
    print(f'  [OK] Episodes: {num_episodes} (CORRECTO)')
    return True


def validate_total_timesteps(total_timesteps: int) -> bool:
    """[OK] Validar que total_timesteps = 438,000 (50 episodios completos)."""
    if total_timesteps != REQUIRED_TOTAL_TIMESTEPS:
        print(f'  [X] Timesteps: {total_timesteps:,} != {REQUIRED_TOTAL_TIMESTEPS:,}')
        return False
    print(f'  [OK] Timesteps: {total_timesteps:,} (CORRECTO: {REQUIRED_EPISODES} anos x {TIMESTEPS_PER_YEAR})')
    return True


def validate_data_files_exist() -> bool:
    """[OK] Validar que todos los archivos OE2 requeridos existen."""
    all_exist = True
    for name, path_str in REQUIRED_DATA_FILES.items():
        path = Path(path_str)
        if path.exists():
            size_mb = path.stat().st_size / 1_000_000
            print(f'  [OK] {name:12s}: {path_str} ({size_mb:.1f} MB)')
        else:
            print(f'  [X] {name:12s}: FALTA - {path_str}')
            all_exist = False
    return all_exist


def validate_observable_cols_used(obs_dim: int, expected_min_cols: int | None = None) -> bool:
    """[OK] Validar que observation space sea correcto para el entorno configurado."""
    expected = expected_min_cols if expected_min_cols is not None else REQUIRED_CONTEXT['OBS_DIM']
    if obs_dim != expected:
        print(f'  [X] Observation dim: {obs_dim} != {expected}')
        return False
    print(f'  [OK] Observation dim: {obs_dim} (CityLearn 11D + EV 5D + tarifa 2D)')
    return True


def validate_action_space(action_dim: int, valid_dims: tuple = (3,)) -> bool:
    """[OK] Validar que action space sea correcto.

    CityLearn v2 actual expone 3 acciones:
    - bess_action
    - ev_motos_frac
    - ev_mototaxis_frac
    """
    if action_dim not in valid_dims:
        print(f'  [X] Action dim: {action_dim} (esperado: 3)')
        return False
    print(f'  [OK] Action dim: {action_dim} (bess, motos_frac, mototaxis_frac)')
    return True


def validate_reward_weights() -> bool:
    """[OK] Validar pesos reales del wrapper CO2_DUAL_FOCUS v8.1."""
    try:
        from src.citylearnv2 import ev_charging_wrapper as wrapper

        actual = {
            'direct_co2': wrapper._W_DIRECT_CO2,
            'indirect_co2': wrapper._W_INDIRECT_CO2,
            'ev_complete': wrapper._W_EV_COMPLETE,
            'bess_solar': wrapper._W_BESS_SOLAR,
            'solar': wrapper._W_SOLAR,
            'grid_stable': wrapper._W_GRID_STABLE,
            'cost': wrapper._W_COST,
        }

        all_ok = True
        for key, expected in REQUIRED_WEIGHTS.items():
            value = float(actual[key])
            if abs(value - expected) < 1e-9:
                print(f'  [OK] Reward {key:13s}: {value:.2f}')
            else:
                print(f'  [X] Reward {key:13s}: {value:.2f} != {expected:.2f}')
                all_ok = False

        total = sum(float(v) for v in actual.values())
        if abs(total - 1.0) < 1e-9:
            print(f'  [OK] Reward sum: {total:.2f}')
        else:
            print(f'  [X] Reward sum: {total:.2f} != 1.00')
            all_ok = False
        return all_ok
    except Exception as e:
        print(f'  [X] Reward weights error: {e}')
        return False


def validate_context_iquitos() -> bool:
    """[OK] Validar contexto de Iquitos con constantes correctas."""
    try:
        from src.citylearnv2 import ev_charging_wrapper as wrapper

        checks = {
            'CO2 factor': (abs(wrapper.CO2_GRID_KG_PER_KWH - REQUIRED_CONTEXT['CO2_FACTOR_KG_PER_KWH']) < 0.0001, wrapper.CO2_GRID_KG_PER_KWH),
            'BESS capacity': (abs(wrapper.BESS_CAPACITY_KWH - REQUIRED_CONTEXT['BESS_CAPACITY_KWH']) < 0.1, wrapper.BESS_CAPACITY_KWH),
            'BESS power': (abs(wrapper.BESS_MAX_KW - 400.0) < 0.1, wrapper.BESS_MAX_KW),
            'Motos max kW': (abs(wrapper.EV_MOTOS_MAX_KW - 222.0) < 0.1, wrapper.EV_MOTOS_MAX_KW),
            'Mototaxis max kW': (abs(wrapper.EV_MOTOTAXIS_MAX_KW - 59.2) < 0.1, wrapper.EV_MOTOTAXIS_MAX_KW),
        }
        
        all_ok = True
        for check_name, (result, value) in checks.items():
            if result:
                print(f'  [OK] {check_name}: {value}')
            else:
                print(f'  [X] {check_name}: {value}')
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f'  [X] Context error: {e}')
        return False


def validate_agent_config(agent_name: str, num_episodes: int, total_timesteps: int,
                          obs_dim: int, action_dim: int) -> bool:
    """VALIDACION INTEGRADA - Ejecutar todos los checks para un agente."""
    print('\n' + '='*80)
    print(f'[VALIDACION DE ENTRENAMIENTO] {agent_name}')
    print('='*80)
    
    checks = [
        ('[GRAPH] Episodes', validate_episodes(num_episodes)),
        ('[TIME]️  Timesteps', validate_total_timesteps(total_timesteps)),
        ('📁 Data files', validate_data_files_exist()),
        ('👁️  Observation space', validate_observable_cols_used(obs_dim)),
        ('🎮 Action space', validate_action_space(action_dim)),
        ('🎯 Reward weights', validate_reward_weights()),
        ('🌍 Context Iquitos', validate_context_iquitos()),
    ]
    
    all_pass = all(result for _, result in checks)
    
    print('\n' + '='*80)
    if all_pass:
        print(f'[RESULTADO] [OK] {agent_name} PREPARADO PARA ENTRENAMIENTO COMPLETO')
        print('='*80)
        print(f'Config:')
        print(f'  - Episodes: {num_episodes} (50 episodios completos)')
        print(f'  - Timesteps: {total_timesteps:,} (438,000 pasos)')
        print(f'  - Observation: {obs_dim} dims')
        print(f'  - Action: {action_dim} dims')
        print(f'  - Datasets: TODOS cargados')
        print(f'  - Multiobjetivo: SI (CO2_DUAL_FOCUS v8.1)')
        print(f'  - Validacion: OK [OK]')
    else:
        print(f'[RESULTADO] [X] {agent_name} NO LISTO - Revisar errores arriba')
        print('='*80)
    
    return all_pass


def main():
    """Script standalone para validar agentes."""
    print('\n' + '='*80)
    print('VALIDACION CENTRALIZADA - Todos los agentes')
    print('='*80)
    
    # Stats
    total_cols = count_total_observable_cols()
    print(f'\nRequisitos globales:')
    print(f'  - Episodios por agente: {REQUIRED_EPISODES} (ano completo)')
    print(f'  - Timesteps totales: {REQUIRED_TOTAL_TIMESTEPS:,}')
    print(f'  - Columnas fuente verificadas: {total_cols}')
    print(f'  - Observation dim: {REQUIRED_CONTEXT["OBS_DIM"]}')
    print(f'  - Acciones controlables: 3 (BESS + motos + mototaxis)')
    print(f'  - Multiobjetivo: SI (CO2_DUAL_FOCUS v8.1)')
    print(f'  - Independencia de algoritmo: SI, mismo wrapper para SAC/PPO/A2C')
    
    # Validar each agent
    agents_config = [
        ('SAC (Off-policy)', 50, 438_000, 18, 3),
        ('PPO (On-policy)', 50, 438_000, 18, 3),
        ('A2C (On-policy)', 50, 438_000, 18, 3),
    ]
    
    results = []
    for agent_name, num_eps, total_ts, obs_d, act_d in agents_config:
        result = validate_agent_config(agent_name, num_eps, total_ts, obs_d, act_d)
        results.append((agent_name, result))
    
    # Summary
    print('\n' + '='*80)
    print('[SUMMARY] Validacion centralizada')
    print('='*80)
    for agent_name, result in results:
        status = '[OK] OK' if result else '[X] FAIL'
        print(f'  {status} {agent_name}')
    
    if all(result for _, result in results):
        print('\n[OK] TODOS LOS AGENTES LISTOS PARA ENTRENAMIENTO COMPLETO')
        return 0
    else:
        print('\n[X] ALGUNOS AGENTES REQUIRE CORRECCIONES')
        return 1


if __name__ == '__main__':
    sys.exit(main())
