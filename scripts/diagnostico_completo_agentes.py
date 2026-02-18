#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO COMPLETO - Verificación de Guardado y Procesamiento de Datos en Agentes RL
Verifica:
1. Estructura de archivos de salida (trace, timeseries, result)
2. Columnas procesadas en datasets
3. Métricas guardadas (costos, CO2 directo/indirecto, motos/mototaxis)
4. Gráficas generadas y paneles vacíos
5. Integridad de datos en timeseries
"""

from __future__ import annotations

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sys
from dataclasses import dataclass

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

OUTPUT_DIR = Path("outputs")
CHECKPOINTS_DIR = Path("checkpoints")
DATA_DIR = Path("data/processed/citylearn/iquitos_ev_mall")

# Agentes a verificar
AGENTS = ["SAC", "PPO", "A2C"]

# Archivos esperados por agente
EXPECTED_FILES = {
    "trace": "{agent_lower}_trace.csv",
    "timeseries": "{agent_lower}_timeseries.csv", 
    "result": "result_{agent_lower}.json",
}

# Columnas CRÍTICAS esperadas en cada archivo
TRACE_COLUMNS_REQUIRED = [
    "step", "timestamp", "reward", "done", "info",
    "observation", "action"
]

TIMESERIES_COLUMNS_REQUIRED = [
    "hour", "solar_w_m2", "grid_hz", 
    "ev_energy_demand_kwh",
    "bess_soc_percent",
    "electricity_consumption_kwh",
    "electricity_cost",
    "carbon_emissions_kg",
    "direct_co2_reduction_motos_kg",
    "direct_co2_reduction_mototaxis_kg",
    "indirect_co2_reduction_solar_kg",
    "motos_charged",
    "mototaxis_charged",
]

RESULT_SECTIONS_REQUIRED = [
    "training",
    "validation", 
    "training_evolution",
    "vehicle_charging",
    "co2_structure_v71",
    "dataset_columns",
]

# ============================================================================
# CLASES AUXILIARES
# ============================================================================

@dataclass
class FileStatus:
    """Estado de un archivo"""
    agent: str
    file_type: str
    exists: bool
    path: Optional[Path] = None
    size_bytes: Optional[int] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    missing_columns: List[str] = None
    
    def __post_init__(self):
        if self.missing_columns is None:
            self.missing_columns = []

@dataclass
class ColumnAnalysis:
    """Análisis de columna individual"""
    column_name: str
    data_type: str
    non_null_count: int
    null_count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    unique_values: Optional[int] = None
    has_zeros: bool = False
    all_zeros: bool = False
    has_negatives: bool = False

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def check_file_exists(file_path: Path) -> FileStatus:
    """Verifica si un archivo existe y obtiene metadatos básicos"""
    agent = file_path.parent.name if file_path.parent.name in AGENTS else "UNKNOWN"
    file_type = file_path.suffix
    
    if not file_path.exists():
        return FileStatus(agent=agent, file_type=file_type, exists=False)
    
    try:
        size_bytes = file_path.stat().st_size
        
        # Detectar tipo de archivo
        if file_path.suffix == ".csv":
            df = pd.read_csv(file_path, nrows=1)
            rows = len(pd.read_csv(file_path))
            columns = len(df.columns)
            return FileStatus(
                agent=agent,
                file_type=file_type,
                exists=True,
                path=file_path,
                size_bytes=size_bytes,
                rows=rows,
                columns=columns,
            )
        elif file_path.suffix == ".json":
            with open(file_path, 'r') as f:
                data = json.load(f)
            return FileStatus(
                agent=agent,
                file_type=file_type,
                exists=True,
                path=file_path,
                size_bytes=size_bytes,
            )
    except Exception as e:
        print(f"ERROR leyendo {file_path}: {e}")
    
    return FileStatus(agent=agent, file_type=file_type, exists=False)

def analyze_dataframe(df: pd.DataFrame, required_columns: List[str]) -> Tuple[List[ColumnAnalysis], List[str]]:
    """Analiza estructura y contenido de DataFrame"""
    analyses = []
    missing = []
    
    for col in df.columns:
        try:
            # Análisis básico
            data_type = str(df[col].dtype)
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            
            analysis = ColumnAnalysis(
                column_name=col,
                data_type=data_type,
                non_null_count=non_null,
                null_count=null_count,
                unique_values=df[col].nunique() if null_count < len(df) else None,
            )
            
            # Análisis numérico si aplica
            if pd.api.types.is_numeric_dtype(df[col]):
                try:
                    analysis.min_value = float(df[col].min())
                    analysis.max_value = float(df[col].max())
                    analysis.mean_value = float(df[col].mean())
                    analysis.std_value = float(df[col].std())
                    analysis.has_zeros = (df[col] == 0).any()
                    analysis.all_zeros = (df[col] == 0).all()
                    analysis.has_negatives = (df[col] < 0).any()
                except:
                    pass
            
            analyses.append(analysis)
        except Exception as e:
            print(f"Error analizando columna {col}: {e}")
    
    # Verificar columnas faltantes
    for req_col in required_columns:
        if req_col not in df.columns:
            missing.append(req_col)
    
    return analyses, missing

def check_empty_panels(df: pd.DataFrame) -> Dict[str, bool]:
    """Verifica paneles vacíos (columnas que deberían tener datos pero no)"""
    empty_panels = {}
    
    # Columnas que NUNCA deben estar todas en cero o todas nulas
    critical_columns = [
        col for col in df.columns 
        if any(metric in col.lower() for metric in [
            'co2', 'cost', 'emission', 'reduction', 'motos', 'charged', 'solar'
        ])
    ]
    
    for col in critical_columns:
        if col not in df.columns:
            continue
            
        # Verificar si todos son ceros o nulos
        all_null_or_zero = (df[col].isna().all()) or ((df[col] == 0).all())
        empty_panels[col] = all_null_or_zero
    
    return empty_panels

# ============================================================================
# VERIFICACIÓN PRINCIPAL
# ============================================================================

def main():
    print("="*100)
    print("DIAGNÓSTICO COMPLETO - AGENTES RL (SAC/PPO/A2C)")
    print("="*100)
    print()
    
    # 1. Verificar estructura de directorios
    print("1. ESTRUCTURA DE DIRECTORIOS")
    print("-"*100)
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        agent_output_dir = OUTPUT_DIR / agent_lower
        
        status = "✓" if agent_output_dir.exists() else "✗"
        print(f"{status} {agent}: {agent_output_dir}")
        
        if agent_output_dir.exists():
            files = list(agent_output_dir.glob("*"))
            for f in files:
                print(f"   └─ {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    
    print()
    
    # 2. Verificar archivos de salida
    print("2. ARCHIVOS DE SALIDA REQUERIDOS")
    print("-"*100)
    
    file_statuses = {}
    for agent in AGENTS:
        agent_lower = agent.lower()
        file_statuses[agent] = {}
        
        print(f"\n{agent}:")
        for file_type, file_pattern in EXPECTED_FILES.items():
            file_name = file_pattern.replace("{agent_lower}", agent_lower)
            file_path = OUTPUT_DIR / agent_lower / file_name
            
            status = check_file_exists(file_path)
            file_statuses[agent][file_type] = status
            
            status_symbol = "✓" if status.exists else "✗"
            if status.exists:
                if status.file_type == ".csv":
                    detail = f"({status.rows:,} rows × {status.columns} cols, {status.size_bytes / 1024:.1f} KB)"
                else:
                    detail = f"({status.size_bytes / 1024:.1f} KB)"
            else:
                detail = "NO ENCONTRADO"
            
            print(f"  {status_symbol} {file_type}: {file_name} {detail}")
    
    print()
    
    # 3. Análisis detallado de trace.csv
    print("3. ANÁLISIS TRACE.CSV (Registro detallado de steps)")
    print("-"*100)
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        trace_file = OUTPUT_DIR / agent_lower / f"{agent_lower}_trace.csv"
        
        if not trace_file.exists():
            print(f"\n{agent}: ARCHIVO NO ENCONTRADO")
            continue
        
        print(f"\n{agent} - {trace_file.name}:")
        try:
            df_trace = pd.read_csv(trace_file)
            print(f"  Dimensiones: {df_trace.shape[0]:,} rows × {df_trace.shape[1]} columns")
            print(f"  Columnas disponibles: {list(df_trace.columns)}")
            
            # Análisis de columnas
            analyses, missing = analyze_dataframe(df_trace, TRACE_COLUMNS_REQUIRED)
            
            if missing:
                print(f"  ⚠ COLUMNAS FALTANTES: {missing}")
            else:
                print(f"  ✓ Todas las columnas requeridas presentes")
            
            # Estadísticas rápidas
            if 'reward' in df_trace.columns:
                print(f"  Reward: min={df_trace['reward'].min():.2f}, max={df_trace['reward'].max():.2f}, mean={df_trace['reward'].mean():.2f}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print()
    
    # 4. Análisis detallado de timeseries.csv
    print("4. ANÁLISIS TIMESERIES.CSV (Series temporales horarias con métricas)")
    print("-"*100)
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        ts_file = OUTPUT_DIR / agent_lower / f"{agent_lower}_timeseries.csv"
        
        if not ts_file.exists():
            print(f"\n{agent}: ARCHIVO NO ENCONTRADO")
            continue
        
        print(f"\n{agent} - {ts_file.name}:")
        try:
            df_ts = pd.read_csv(ts_file)
            print(f"  Dimensiones: {df_ts.shape[0]:,} rows × {df_ts.shape[1]} columns")
            print(f"  Horas: {df_ts.shape[0]} (esperado: 8,760 = 1 año)")
            
            if df_ts.shape[0] != 8760:
                print(f"  ⚠ ADVERTENCIA: {df_ts.shape[0]} horas != 8760")
            
            # Columnas disponibles
            print(f"\n  Columnas disponibles ({len(df_ts.columns)}):")
            for i, col in enumerate(df_ts.columns, 1):
                dtype = str(df_ts[col].dtype)
                print(f"    {i:2d}. {col:40s} ({dtype})")
            
            # Verificar columnas críticas
            print(f"\n  COLUMNAS CRÍTICAS:")
            critical_cols = [
                'solar_w_m2', 'grid_hz', 'ev_energy_demand_kwh', 'bess_soc_percent',
                'electricity_consumption_kwh', 'electricity_cost', 'carbon_emissions_kg',
                'direct_co2_reduction_motos_kg', 'direct_co2_reduction_mototaxis_kg',
                'indirect_co2_reduction_solar_kg', 'motos_charged', 'mototaxis_charged'
            ]
            
            for col in critical_cols:
                if col in df_ts.columns:
                    non_null = df_ts[col].notna().sum()
                    unique = df_ts[col].nunique()
                    status = "✓" if non_null > 0 and unique > 1 else "⚠"
                    print(f"    {status} {col:40s} (values: {non_null:,}, unique: {unique})")
                else:
                    print(f"    ✗ {col:40s} FALTANTE")
            
            # Verificar paneles vacíos
            print(f"\n  DETECCIÓN DE PANELES VACÍOS:")
            empty_panels = check_empty_panels(df_ts)
            has_empty = any(empty_panels.values())
            
            if has_empty:
                for col, is_empty in empty_panels.items():
                    if is_empty:
                        print(f"    ✗ {col}: TODO CEROS O NULO")
            else:
                print(f"    ✓ Sin paneles vacíos detectados")
            
            # Estadísticas de columnas numéricas clave
            print(f"\n  ESTADÍSTICAS DE MÉTRICAS CLAVE:")
            for col in ['electricity_cost', 'carbon_emissions_kg', 'motos_charged', 'mototaxis_charged']:
                if col in df_ts.columns:
                    try:
                        stats = {
                            'min': df_ts[col].min(),
                            'max': df_ts[col].max(),
                            'mean': df_ts[col].mean(),
                            'sum': df_ts[col].sum(),
                        }
                        print(f"    {col:30s}: min={stats['min']:8.2f}, max={stats['max']:8.2f}, mean={stats['mean']:8.2f}, total={stats['sum']:12.2f}")
                    except:
                        pass
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print()
    
    # 5. Análisis de result.json
    print("5. ANÁLISIS RESULT_*.JSON (Resumen completo)")
    print("-"*100)
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        result_file = OUTPUT_DIR / agent_lower / f"result_{agent_lower}.json"
        
        if not result_file.exists():
            print(f"\n{agent}: ARCHIVO NO ENCONTRADO")
            continue
        
        print(f"\n{agent} - {result_file.name}:")
        try:
            with open(result_file, 'r') as f:
                result_data = json.load(f)
            
            # Secciones principales
            print(f"  Secciones principales:")
            for section in RESULT_SECTIONS_REQUIRED:
                status = "✓" if section in result_data else "✗"
                print(f"    {status} {section}")
            
            # Información de entrenamiento
            if 'training' in result_data:
                train = result_data['training']
                print(f"\n  Training Info:")
                print(f"    - Total timesteps: {train.get('total_timesteps', '?'):,}")
                print(f"    - Episodes: {train.get('episodes', '?')}")
                print(f"    - Duration: {train.get('duration_seconds', '?'):.1f}s")
                print(f"    - Device: {train.get('device', '?')}")
            
            # Información de validación
            if 'validation' in result_data:
                val = result_data['validation']
                print(f"\n  Validation Metrics:")
                print(f"    - Mean reward: {val.get('mean_reward', 'N/A')}")
                print(f"    - Mean CO2 avoided: {val.get('mean_co2_avoided_kg', 'N/A'):.0f} kg")
                print(f"    - Mean solar: {val.get('mean_solar_kwh', 'N/A'):.2f} kWh")
                print(f"    - Mean grid import: {val.get('mean_grid_import_kwh', 'N/A'):.2f} kWh")
            
            # Información de vehículos
            if 'vehicle_charging' in result_data:
                veh = result_data['vehicle_charging']
                motos_list = veh.get('motos_charged_per_episode', [])
                taxis_list = veh.get('mototaxis_charged_per_episode', [])
                
                print(f"\n  Vehicle Charging:")
                if motos_list:
                    print(f"    - Motos: {len(motos_list)} episodios, promedio: {np.mean(motos_list):.1f}/día")
                else:
                    print(f"    - Motos: SIN DATOS")
                
                if taxis_list:
                    print(f"    - Mototaxis: {len(taxis_list)} episodios, promedio: {np.mean(taxis_list):.1f}/día")
                else:
                    print(f"    - Mototaxis: SIN DATOS")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print()
    
    # 6. Verificación de columnas en datasets originales
    print("6. VERIFICACIÓN DE COLUMNAS EN DATASETS ORIGINALES")
    print("-"*100)
    
    dataset_files = [
        "data/processed/citylearn/iquitos_ev_mall/citylearnv2_combined_dataset.csv",
        "data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv",
        "data/processed/citylearn/iquitos_ev_mall/chargers_timeseries.csv",
        "data/processed/citylearn/iquitos_ev_mall/solar_generation.csv",
        "data/processed/citylearn/iquitos_ev_mall/mall_demand.csv",
    ]
    
    for dataset_path in dataset_files:
        file = Path(dataset_path)
        if file.exists():
            try:
                df = pd.read_csv(file, nrows=10)
                print(f"\n✓ {file.name}")
                print(f"  Columnas: {len(df.columns)}")
                print(f"  Primeras columnas: {list(df.columns[:5])}")
            except Exception as e:
                print(f"\n✗ {file.name}: ERROR ({e})")
        else:
            print(f"\n✗ {file.name}: NO ENCONTRADO")
    
    print()
    
    # 7. Resumen y recomendaciones
    print("7. RESUMEN Y RECOMENDACIONES")
    print("-"*100)
    
    missing_agents = []
    incomplete_agents = []
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        
        has_trace = (OUTPUT_DIR / agent_lower / f"{agent_lower}_trace.csv").exists()
        has_ts = (OUTPUT_DIR / agent_lower / f"{agent_lower}_timeseries.csv").exists()
        has_result = (OUTPUT_DIR / agent_lower / f"result_{agent_lower}.json").exists()
        
        if not (has_trace and has_ts and has_result):
            incomplete_agents.append(agent)
        elif not (has_trace and has_ts):
            incomplete_agents.append(agent)
    
    print("\n📊 ESTADO GENERAL:")
    if not incomplete_agents:
        print("  ✓ Todos los agentes tienen archivos completos")
    else:
        print(f"  ⚠ Agentes con archivos incompletos: {', '.join(incomplete_agents)}")
    
    print("\n🎯 PRÓXIMAS ACCIONES RECOMENDADAS:")
    print("  1. Ejecutar agentes si no tienen archivos completos")
    print("  2. Verificar que trace.csv tenga >1000 registros (mínimo)")
    print("  3. Verificar que timeseries.csv sea exactamente 8760 horas")
    print("  4. Revisar paneles vacíos en gráficas generadas")
    print("  5. Comparar métricas entre SAC vs PPO vs A2C")
    print()
    
    print("="*100)
    print("FIN DEL DIAGNÓSTICO")
    print("="*100)

if __name__ == "__main__":
    main()
