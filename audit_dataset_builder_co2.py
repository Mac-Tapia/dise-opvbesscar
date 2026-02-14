#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA DATASET_BUILDER - VALIDACION CO2 DIRECTO E INDIRECTO
==============================================================================
Verifica que dataset_builder.py está considerando correctamente:
  [1] Columnas de REDUCCION DIRECTA de CO2 (EVs - fuel switch)
  [2] Columnas de REDUCCION INDIRECTA de CO2 (Solar - grid import avoided)
  [3] Calculo y tracking de CO2 acumulado anual
  [4] Variables observables para agentes RL

Creado: 2026-02-13
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


# ============================================================================
# VARIABLES ESPERADAS EN DATASET_BUILDER.PY
# ============================================================================

EXPECTED_CO2_VARIABLES = {
    # REDUCCION DIRECTA (EVs)
    'DIRECT_CO2': {
        'FACTOR_CO2_GASOLINA_KG_L': ('2.31', 'kg CO2/L gasolina (IPCC AR5)'),
        'FACTOR_CO2_NETO_MOTO_KG_KWH': ('0.87', 'kg CO2/kWh evitado neto (moto fuel switch)'),
        'FACTOR_CO2_NETO_MOTOTAXI_KG_KWH': ('0.47', 'kg CO2/kWh evitado neto (mototaxi)'),
    },
    # REDUCCION INDIRECTA (Solar)
    'INDIRECT_CO2': {
        'FACTOR_CO2_RED_KG_KWH': ('0.4521', 'kg CO2/kWh - red diésel Iquitos (grid import avoided)'),
    }
}

EXPECTED_CHARGER_COLUMNS = {
    'ev_energia_motos_kwh': 'Energía carga motos por hora',
    'ev_energia_mototaxis_kwh': 'Energía carga mototaxis por hora',
    'co2_reduccion_motos_kg': 'CO2 reducción motos (directo)',
    'co2_reduccion_mototaxis_kg': 'CO2 reducción mototaxis (directo)',
    'reduccion_directa_co2_kg': 'CO2 reducción directa TOTAL (EVs)',
}

EXPECTED_SOLAR_COLUMNS = {
    'reduccion_indirecta_co2_kg': 'CO2 reducción indirecta por solar',
    'co2_evitado_mall_kg': 'CO2 evitado asignado a Mall (67%)',
    'co2_evitado_ev_kg': 'CO2 evitado asignado a EV (33%)',
}

EXPECTED_OBSERVABLE_COLS = [
    'ev_reduccion_directa_co2_kg',    # Total CO2 directo
    'solar_reduccion_indirecta_co2_kg', # Total CO2 indirecto
    'total_reduccion_co2_kg',           # Combinado
]


# ============================================================================
# SCANNER
# ============================================================================

def read_file(filepath: Path) -> str:
    """Leer archivo con encoding UTF-8."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def check_constants_defined(content: str) -> Dict[str, Tuple[bool, str]]:
    """Verificar que las constantes CO2 estén definidas."""
    results = {}
    
    # Buscar DIRECT CO2
    for const_name, (expected_val, desc) in EXPECTED_CO2_VARIABLES['DIRECT_CO2'].items():
        pattern = rf'{const_name}\s*[=:]\s*({re.escape(expected_val)}|[\d.]+)'
        match = re.search(pattern, content)
        found = match is not None
        value = match.group(1) if match else 'NOT FOUND'
        results[const_name] = (found, f"{desc} = {value}")
    
    # Buscar INDIRECT CO2
    for const_name, (expected_val, desc) in EXPECTED_CO2_VARIABLES['INDIRECT_CO2'].items():
        pattern = rf'{const_name}\s*[=:]\s*({re.escape(expected_val)}|[\d.]+)'
        match = re.search(pattern, content)
        found = match is not None
        value = match.group(1) if match else 'NOT FOUND'
        results[const_name] = (found, f"{desc} = {value}")
    
    return results


def check_charger_observable_columns(content: str) -> Dict[str, Tuple[bool, str]]:
    """Verificar que se extraigan columnas de CO2 directo de chargers."""
    results = {}
    
    for col_name, desc in EXPECTED_CHARGER_COLUMNS.items():
        # Buscar referencia a la columna en _extract_observable_variables
        patterns = [
            rf"'{col_name}'",
            rf'"{col_name}"',
            rf'\["{col_name}"\]',
            rf"\['{col_name}'\]",
        ]
        
        found = any(re.search(p, content) for p in patterns)
        results[col_name] = (found, desc)
    
    return results


def check_solar_observable_columns(content: str) -> Dict[str, Tuple[bool, str]]:
    """Verificar que se extraigan columnas de CO2 indirecto de solar."""
    results = {}
    
    for col_name, desc in EXPECTED_SOLAR_COLUMNS.items():
        patterns = [
            rf"'{col_name}'",
            rf'"{col_name}"',
            rf'\["{col_name}"\]',
            rf"\['{col_name}'\]",
        ]
        
        found = any(re.search(p, content) for p in patterns)
        results[col_name] = (found, desc)
    
    return results


def check_observable_calculations(content: str) -> Dict[str, Tuple[bool, str]]:
    """Verificar que se calculen variables observables combinadas."""
    results = {}
    
    for col_name in EXPECTED_OBSERVABLE_COLS:
        # Buscar cálculo de la columna
        patterns = [
            rf"obs_df\['{col_name}'\]",
            rf'obs_df\["{col_name}"\]',
            rf"{col_name}\s*=",
        ]
        
        found = any(re.search(p, content) for p in patterns)
        results[col_name] = (found, f"Cálculo/asignación de {col_name}")
    
    return results


def check_co2_tracking_logic(content: str) -> List[Tuple[str, bool]]:
    """Verificar que existe lógica de tracking CO2."""
    checks = [
        ('Direct CO2 calculation (EVs)', 'reduccion_directa_co2' in content),
        ('Indirect CO2 calculation (Solar)', 'reduccion_indirecta_co2' in content),
        ('CO2 combination/sum', 'total_reduccion_co2' in content),
        ('CO2 logging/reporting', 'total_reduccion_co2' in content and 'ton' in content.lower()),
        ('Observable variables extraction', '_extract_observable_variables' in content),
        ('BESS CO2 handling (v5.4)', 'bess_df' in content or 'bess_co2' in content),
    ]
    
    return checks


def check_context_integration(content: str) -> Dict[str, Tuple[bool, str]]:
    """Verificar que se integre IquitosContext para factores CO2."""
    results = {}
    
    checks = {
        'IquitosContext': 'Importación de contexto Iquitos (CO2 factors)',
        'create_iquitos_reward_weights': 'Carga de pesos multiobjetivo',
        'co2_factor_kg_per_kwh': 'Factor CO2 grid en contexto',
        'REWARDS_AVAILABLE': 'Verificación de disponibilidad rewards',
    }
    
    for keyword, desc in checks.items():
        found = keyword in content
        results[keyword] = (found, desc)
    
    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecutar auditoría completa."""
    
    print('=' * 90)
    print('AUDITORIA DATASET_BUILDER - VALIDACION CO2 DIRECTO E INDIRECTO')
    print('=' * 90)
    print()
    
    filepath = Path('src/citylearnv2/dataset_builder/dataset_builder.py')
    
    if not filepath.exists():
        print(f'❌ Archivo no encontrado: {filepath}')
        return
    
    content = read_file(filepath)
    
    # [1] VERIFICAR CONSTANTES CO2
    print('\n[1] CONSTANTES CO2 (DIRECTA E INDIRECTA)')
    print('-' * 90)
    
    constants = check_constants_defined(content)
    
    direct_ok = 0
    indirect_ok = 0
    
    print('\n  📊 REDUCCION DIRECTA (EVs - Fuel Switch):')
    for const_name, (found, info) in constants.items():
        if const_name in EXPECTED_CO2_VARIABLES['DIRECT_CO2']:
            status = '✅' if found else '❌'
            print(f'     {status} {const_name:45s} {info}')
            if found:
                direct_ok += 1
    
    print('\n  📊 REDUCCION INDIRECTA (Solar - Grid Import):')
    for const_name, (found, info) in constants.items():
        if const_name in EXPECTED_CO2_VARIABLES['INDIRECT_CO2']:
            status = '✅' if found else '❌'
            print(f'     {status} {const_name:45s} {info}')
            if found:
                indirect_ok += 1
    
    total_constants = len(EXPECTED_CO2_VARIABLES['DIRECT_CO2']) + len(EXPECTED_CO2_VARIABLES['INDIRECT_CO2'])
    constants_found = direct_ok + indirect_ok
    
    print(f'\n  Estado: {constants_found}/{total_constants} constantes detectadas')
    
    # [2] COLUMNAS DE CHARGERS (CO2 DIRECTO)
    print('\n[2] COLUMNAS CHARGERS - REDUCCION DIRECTA CO2')
    print('-' * 90)
    
    charger_cols = check_charger_observable_columns(content)
    charger_ok = sum(1 for found, _ in charger_cols.values() if found)
    
    print('\n  📋 Variables esperadas en chargers:')
    for col_name, (found, desc) in charger_cols.items():
        status = '✅' if found else '❌'
        print(f'     {status} {col_name:45s} {desc}')
    
    print(f'\n  Estado: {charger_ok}/{len(charger_cols)} columnas detectadas')
    
    # [3] COLUMNAS DE SOLAR (CO2 INDIRECTO)
    print('\n[3] COLUMNAS SOLAR - REDUCCION INDIRECTA CO2')
    print('-' * 90)
    
    solar_cols = check_solar_observable_columns(content)
    solar_ok = sum(1 for found, _ in solar_cols.values() if found)
    
    print('\n  📋 Variables esperadas en solar:')
    for col_name, (found, desc) in solar_cols.items():
        status = '✅' if found else '❌'
        print(f'     {status} {col_name:45s} {desc}')
    
    print(f'\n  Estado: {solar_ok}/{len(solar_cols)} columnas detectadas')
    
    # [4] CALCULOS DE OBSERVABLES
    print('\n[4] CALCULOS DE VARIABLES OBSERVABLES (COMBINADAS)')
    print('-' * 90)
    
    obs_calcs = check_observable_calculations(content)
    obs_ok = sum(1 for found, _ in obs_calcs.values() if found)
    
    print('\n  📊 Variables combinadas (directo + indirecto):')
    for col_name, (found, desc) in obs_calcs.items():
        status = '✅' if found else '❌'
        print(f'     {status} {col_name:45s} {desc}')
    
    print(f'\n  Estado: {obs_ok}/{len(obs_calcs)} cálculos detectados')
    
    # [5] LOGICA DE TRACKING
    print('\n[5] LOGICA DE TRACKING CO2')
    print('-' * 90)
    
    tracking = check_co2_tracking_logic(content)
    tracking_ok = sum(1 for _, found in tracking if found)
    
    print('\n  🔍 Validaciones de tracking:')
    for desc, found in tracking:
        status = '✅' if found else '❌'
        print(f'     {status} {desc}')
    
    print(f'\n  Estado: {tracking_ok}/{len(tracking)} validaciones pasadas')
    
    # [6] INTEGRACION CON CONTEXTO
    print('\n[6] INTEGRACION CON IQUITOS CONTEXT (REWARDS)')
    print('-' * 90)
    
    context = check_context_integration(content)
    context_ok = sum(1 for found, _ in context.values() if found)
    
    print('\n  🔗 Integración con rewards.py:')
    for keyword, (found, desc) in context.items():
        status = '✅' if found else '❌'
        print(f'     {status} {keyword:45s} {desc}')
    
    print(f'\n  Estado: {context_ok}/{len(context)} integraciones detectadas')
    
    # [7] RESUMEN FINAL
    print('\n' + '=' * 90)
    print('RESUMEN FINAL')
    print('=' * 90)
    
    total_checks = constants_found + charger_ok + solar_ok + obs_ok + tracking_ok + context_ok
    total_expected = total_constants + len(charger_cols) + len(solar_cols) + len(obs_calcs) + len(tracking) + len(context)
    
    print(f'\n  Total detectado: {total_checks}/{total_expected}')
    
    # Análisis detallado
    print('\n  📊 DESGLOSE POR CATEGORIA:')
    print(f'     ├─ Constantes CO2:        {constants_found}/{total_constants} ✅' if constants_found == total_constants else f'     ├─ Constantes CO2:        {constants_found}/{total_constants} ❌')
    print(f'     ├─ Columnas Chargers:     {charger_ok}/{len(charger_cols)} ✅' if charger_ok == len(charger_cols) else f'     ├─ Columnas Chargers:     {charger_ok}/{len(charger_cols)} ❌')
    print(f'     ├─ Columnas Solar:        {solar_ok}/{len(solar_cols)} ✅' if solar_ok == len(solar_cols) else f'     ├─ Columnas Solar:        {solar_ok}/{len(solar_cols)} ❌')
    print(f'     ├─ Cálculos Observables:  {obs_ok}/{len(obs_calcs)} ✅' if obs_ok == len(obs_calcs) else f'     ├─ Cálculos Observables:  {obs_ok}/{len(obs_calcs)} ❌')
    print(f'     ├─ Tracking Logic:        {tracking_ok}/{len(tracking)} ✅' if tracking_ok == len(tracking) else f'     ├─ Tracking Logic:        {tracking_ok}/{len(tracking)} ❌')
    print(f'     └─ Integración Rewards:   {context_ok}/{len(context)} ✅' if context_ok == len(context) else f'     └─ Integración Rewards:   {context_ok}/{len(context)} ❌')
    
    # Determinar estado final
    all_ok = (constants_found == total_constants and 
              charger_ok == len(charger_cols) and 
              solar_ok == len(solar_cols) and 
              obs_ok == len(obs_calcs) and 
              tracking_ok == len(tracking) and 
              context_ok == len(context))
    
    print()
    if all_ok:
        print('  🎯 RESULTADO: ✅ DATASET_BUILDER ESTA CONSIDERANDO CORRECTAMENTE CO2 DIRECTO E INDIRECTO')
    else:
        print('  🎯 RESULTADO: ⚠️  DATASET_BUILDER NECESITA ACTUALIZACION')
        print('\n  📝 RECOMENDACIONES:')
        if constants_found < total_constants:
            print('     - Verificar que todas las constantes CO2 estén definidas')
        if charger_ok < len(charger_cols):
            print('     - Verificar extracción de columnas CO2 directo (chargers)')
        if solar_ok < len(solar_cols):
            print('     - Verificar extracción de columnas CO2 indirecto (solar)')
        if obs_ok < len(obs_calcs):
            print('     - Verificar cálculos de variables observables combinadas')
        if tracking_ok < len(tracking):
            print('     - Verificar implementación de tracking logic CO2')
        if context_ok < len(context):
            print('     - Verificar integración con IquitosContext (rewards.py)')
    
    print()


if __name__ == '__main__':
    main()
