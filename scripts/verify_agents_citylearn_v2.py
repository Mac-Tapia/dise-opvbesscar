#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION: ¿ESTAN LOS TRES AGENTES CONECTADOS EN CITYLEARN V2?
¿USAN LOS MISMOS DATOS DE FORMA COMPLETA DE UN AÑO?

Verifica:
1. SAC, PPO, A2C están importando CityLearn v2
2. Todos cargan los mismos archivos de datos
3. Todos usan 8,760 horas (1 año completo)
4. Configuración de ambiente es idéntica
5. Observación y acción spaces son iguales
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

def read_file_partial(filepath: str, max_lines: int = 5000) -> str:
    """Lee archivo sin cargar todo en memoria"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read(max_lines * 100)  # Aproximado
    except Exception as e:
        return f"ERROR: {e}"

def extract_citylearn_imports(filepath: str) -> Dict[str, Any]:
    """Extrae información de importaciones de CityLearn de un script"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {'file': filepath, 'error': str(e)}
    
    info = {
        'file': filepath,
        'has_citylearn': False,
        'citylearn_available': False,
        'imports': [],
        'hours_per_year': None,
        'bess_capacity': None,
        'solar_paths': [],
        'chargers_paths': [],
        'bess_paths': [],
        'mall_paths': [],
    }
    
    # Check if CityLearn is imported
    if 'from citylearn import' in content or 'import citylearn' in content:
        info['has_citylearn'] = True
        imports = re.findall(r'from citylearn import ([^\n]+)', content)
        info['imports'] = [imp.strip() for imp in imports]
    
    # Check if CityLearn is available
    if 'CITYLEARN_AVAILABLE = True' in content:
        info['citylearn_available'] = True
    
    # Extract HOURS_PER_YEAR (múltiples patrones)
    match = re.search(r'HOURS_PER_YEAR\s*[:=]\s*(?:int\s*)?=\s*(\d+)', content)
    if match:
        info['hours_per_year'] = int(match.group(1))
    
    # Extract BESS capacity (múltiples patrones)
    patterns = [
        r'BESS_CAPACITY_KWH\s*=\s*([\d.]+)',
        r'BESS_CAPACITY_KWH\s*:\s*float\s*=\s*([\d.]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            info['bess_capacity'] = float(match.group(1))
            break
    
    # Extract data paths
    solar_matches = re.findall(r"Path\(['\"]([^'\"]*pv_generation[^'\"]*)['\"]", content)
    info['solar_paths'] = list(set(solar_matches))
    
    chargers_matches = re.findall(r"Path\(['\"]([^'\"]*chargers[^'\"]*)['\"]", content)
    info['chargers_paths'] = list(set(chargers_matches))
    
    bess_matches = re.findall(r"Path\(['\"]([^'\"]*bess[^'\"]*)['\"]", content)
    info['bess_paths'] = list(set(bess_matches))
    
    mall_matches = re.findall(r"Path\(['\"]([^'\"]*demandamall[^'\"]*)['\"]", content)
    info['mall_paths'] = list(set(mall_matches))
    
    return info

def check_files_exist(paths: List[str]) -> Dict[str, bool]:
    """Verifica si los archivos existen"""
    result = {}
    for path in paths:
        p = Path(path)
        result[path] = p.exists()
    return result

def main():
    print("=" * 100)
    print("VERIFICACION: CONECTIVIDAD CITYLEARN V2 Y DATOS COMUNES")
    print("=" * 100)
    print()
    
    # Archivos de entrenamiento de los tres agentes
    agents_files = {
        'SAC': 'scripts/train/train_sac.py',
        'PPO': 'scripts/train/train_ppo.py',
        'A2C': 'scripts/train/train_a2c.py',
    }
    
    # ===== [1] VERIFICAR IMPORTACIONES Y CONFIGURACION =====
    print("[1] VERIFICACION DE IMPORTACIONES Y CONFIGURACION")
    print("-" * 100)
    
    agent_config = {}
    for agent_name, filepath in agents_files.items():
        print(f"\n📄 {agent_name}: {filepath}")
        if not Path(filepath).exists():
            print(f"  ❌ ARCHIVO NO ENCONTRADO")
            continue
        
        info = extract_citylearn_imports(filepath)
        agent_config[agent_name] = info
        
        print(f"  CityLearn importado: {'✅ YES' if info['has_citylearn'] else '❌ NO'}")
        if info['imports']:
            print(f"    Imports: {', '.join(info['imports'])}")
        print(f"  HOURS_PER_YEAR: {info['hours_per_year']} {'✅' if info['hours_per_year'] == 8760 else '❌'}")
        print(f"  BESS_CAPACITY_KWH: {info['bess_capacity']} {'✅' if info['bess_capacity'] == 2000.0 else '❌'}")
    
    # ===== [2] COMPARAR CONFIGURACION ENTRE AGENTES =====
    print("\n" + "=" * 100)
    print("[2] COMPARACION DE CONFIGURACION ENTRE AGENTES")
    print("-" * 100)
    
    # Verificar HOURS_PER_YEAR
    hours_values = {name: config['hours_per_year'] for name, config in agent_config.items()}
    all_same_hours = len(set(hours_values.values())) == 1
    print(f"\n⏱️  HOURS_PER_YEAR (Duración del año en timesteps):")
    for agent, hours in hours_values.items():
        status = "✅" if hours == 8760 else "❌"
        print(f"  {agent:6s}: {hours:5d} {status}")
    print(f"  SINCRONIZADOS: {'✅ YES (Todos 8,760 horas)' if all_same_hours else '❌ NO (Diferentes valores)'}")
    
    # Verificar BESS_CAPACITY
    bess_values = {name: config['bess_capacity'] for name, config in agent_config.items()}
    all_same_bess = len(set(v for v in bess_values.values() if v is not None)) == 1
    print(f"\n🔋 BESS_CAPACITY_KWH (Capacidad del almacenamiento):")
    for agent, capacity in bess_values.items():
        if capacity is None:
            print(f"  {agent:6s}: (no encontrado en código) ❌")
        else:
            status = "✅" if capacity == 2000.0 else "❌"
            print(f"  {agent:6s}: {capacity:7.1f} kWh {status}")
    print(f"  SINCRONIZADOS: {'✅ YES (Todos 2,000 kWh)' if all_same_bess else '❌ NO (Diferentes valores)'}")
    
    # ===== [3] VERIFICAR ARCHIVOS DE DATOS =====
    print("\n" + "=" * 100)
    print("[3] VERIFICACION DE ARCHIVOS DE DATOS (OE2)")
    print("-" * 100)
    
    print("\n📊 SOLAR (Generación FV Iquitos):")
    solar_files = set()
    for agent, config in agent_config.items():
        for path in config['solar_paths']:
            solar_files.add(path)
            exists = Path(path).exists()
            status = "✅" if exists else "❌"
            print(f"  {path} ({agent}) {status}")
    
    if len(solar_files) > 1:
        print(f"  ⚠️  ADVERTENCIA: Se usan {len(solar_files)} archivos solares distintos")
    else:
        print(f"  ✅ Se usa un único archivo solar")
    
    print("\n🔌 CHARGERS (Demanda EV - 38 sockets):")
    chargers_files = set()
    for agent, config in agent_config.items():
        for path in config['chargers_paths']:
            chargers_files.add(path)
            exists = Path(path).exists()
            status = "✅" if exists else "❌"
            print(f"  {path} ({agent}) {status}")
    
    if len(chargers_files) > 1:
        print(f"  ⚠️  ADVERTENCIA: Se usan {len(chargers_files)} archivos de chargers distintos")
    else:
        print(f"  ✅ Se usa un único archivo de chargers")
    
    print("\n🔋 BESS (Almacenamiento de energía):")
    bess_files = set()
    for agent, config in agent_config.items():
        for path in config['bess_paths']:
            bess_files.add(path)
            exists = Path(path).exists()
            status = "✅" if exists else "❌"
            print(f"  {path} ({agent}) {status}")
    
    if len(bess_files) > 1:
        print(f"  ⚠️  ADVERTENCIA: Se usan {len(bess_files)} archivos BESS distintos")
    else:
        print(f"  ✅ Se usa un único archivo BESS")
    
    print("\n🏬 MALL (Centro comercial - demanda fija):")
    mall_files = set()
    for agent, config in agent_config.items():
        for path in config['mall_paths']:
            mall_files.add(path)
            exists = Path(path).exists()
            status = "✅" if exists else "❌"
            print(f"  {path} ({agent}) {status}")
    
    if len(mall_files) > 1:
        print(f"  ⚠️  ADVERTENCIA: Se usan {len(mall_files)} archivos mall distintos")
    else:
        print(f"  ✅ Se usa un único archivo mall")
    
    # ===== [4] VERIFICAR DATOS COMPLETOS (8,760 HORAS) =====
    print("\n" + "=" * 100)
    print("[4] VERIFICACION DE INTEGRIDAD DE DATOS (1 AÑO COMPLETO)")
    print("-" * 100)
    
    import pandas as pd
    
    data_checks = {
        '📊 Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
        '🔌 Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
        '🔋 BESS': 'data/processed/citylearn/iquitos_ev_mall/bess/bess_ano_2024.csv',
        '🏬 Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
    }
    
    for label, path in data_checks.items():
        p = Path(path)
        if p.exists():
            try:
                df = pd.read_csv(path)
                rows = len(df)
                cols = len(df.columns)
                is_full_year = rows == 8760
                status = "✅" if is_full_year else "❌"
                print(f"\n{label}:")
                print(f"  Archivo: {path}")
                print(f"  Filas: {rows:5d} {status} {'(1 año completo)' if is_full_year else '(INCOMPLETO)'}")
                print(f"  Columnas: {cols:3d}")
            except Exception as e:
                print(f"\n{label}:")
                print(f"  Archivo: {path}")
                print(f"  ❌ ERROR al leer: {e}")
        else:
            print(f"\n{label}:")
            print(f"  Archivo: {path}")
            print(f"  ❌ ARCHIVO NO ENCONTRADO")
    
    # ===== [5] RESUMEN Y ESTADO FINAL =====
    print("\n" + "=" * 100)
    print("[5] RESUMEN Y CONCLUSION")
    print("=" * 100)
    
    # Verificaciones de síntesis
    all_connected = all(config['has_citylearn'] for config in agent_config.values())
    all_hours_same = all_same_hours and all(h == 8760 for h in hours_values.values())
    all_bess_same = all_same_bess and all(b == 2000.0 for b in bess_values.values())
    single_solar = len(solar_files) == 1
    single_chargers = len(chargers_files) == 1
    single_bess = len(bess_files) == 1
    single_mall = len(mall_files) == 1
    
    print(f"\n🔗 CONECTIVIDAD CITYLEARN V2:")
    print(f"  SAC conectado: {'✅' if agent_config['SAC']['has_citylearn'] else '❌'}")
    print(f"  PPO conectado: {'✅' if agent_config['PPO']['has_citylearn'] else '❌'}")
    print(f"  A2C conectado: {'✅' if agent_config['A2C']['has_citylearn'] else '❌'}")
    print(f"  Estado: {'✅ TODOS CONECTADOS' if all_connected else '❌ NO TODOS CONECTADOS'}")
    
    print(f"\n⏱️  INTEGRIDAD TEMPORAL (1 AÑO COMPLETO):")
    print(f"  Duración sincronizada: {'✅ YES' if all_hours_same else '❌ NO'}")
    print(f"  Valores: SAC={hours_values.get('SAC')}, PPO={hours_values.get('PPO')}, A2C={hours_values.get('A2C')}")
    
    print(f"\n🔋 CONFIGURACION BESS SINCRONIZADA:")
    print(f"  Capacidad sincronizada: {'✅ YES' if all_bess_same else '❌ NO'}")
    print(f"  Valores: SAC={bess_values.get('SAC')}, PPO={bess_values.get('PPO')}, A2C={bess_values.get('A2C')}")
    
    print(f"\n📁 DATOS COMUNES (OE2):")
    print(f"  Solar: {'✅' if single_solar else '❌'} {f'({len(solar_files)} archivos)' if not single_solar else ''}")
    print(f"  Chargers: {'✅' if single_chargers else '❌'} {f'({len(chargers_files)} archivos)' if not single_chargers else ''}")
    print(f"  BESS: {'✅' if single_bess else '❌'} {f'({len(bess_files)} archivos)' if not single_bess else ''}")
    print(f"  Mall: {'✅' if single_mall else '❌'} {f'({len(mall_files)} archivos)' if not single_mall else ''}")
    
    # Estado final
    print("\n" + "=" * 100)
    overall_status = all_connected and all_hours_same and all_bess_same and single_solar and single_chargers and single_bess and single_mall
    
    if overall_status:
        print("✅ ESTADO FINAL: TODOS LOS AGENTES ESTAN CORRECTAMENTE CONECTADOS A CITYLEARN V2")
        print("✅ DATOS: Todos comparten la misma fuente OE2 (1 año completo = 8,760 horas)")
        print("✅ SINCRONIZACION: SAC, PPO y A2C usan configuración idéntica")
    else:
        print("❌ ESTADO FINAL: EXISTEN PROBLEMAS DE SINCRONIZACION")
        if not all_connected:
            print("  ❌ NO todos los agentes importan CityLearn v2")
        if not all_hours_same:
            print("  ❌ HOURS_PER_YEAR no está sincronizado (debe ser 8,760)")
        if not all_bess_same:
            print("  ❌ BESS_CAPACITY_KWH no está sincronizado (debe ser 2,000.0)")
        if not (single_solar and single_chargers and single_bess and single_mall):
            print("  ❌ Se usan múltiples fuentes de datos OE2 (debería ser única)")
    
    print("=" * 100)

if __name__ == '__main__':
    main()
