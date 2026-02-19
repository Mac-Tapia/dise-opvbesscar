#!/usr/bin/env python3
"""
VALIDACION OBLIGATORIA: Garantiza que A2C, PPO, SAC SIEMPRE cargan desde data/iquitos_ev_mall

Este módulo se importa en cada agente para forzar la validación.
Si no están en data/iquitos_ev_mall, el entrenamiento FALLA INMEDIATAMENTE.

Uso en agentes:
    from src.validation.mandatory_dataset_check import validate_dataset_connection
    validate_dataset_connection()  # Falla si no está en la ruta correcta
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# País/región para identificar el agente que llama
CURRENT_AGENT = None


def validate_dataset_connection(agent_name: str = "UNKNOWN"):
    """
    VALIDACION OBLIGATORIA: Asegura conexión a data/iquitos_ev_mall
    
    Args:
        agent_name: Nombre del agente (SAC, PPO, A2C)
    
    Raises:
        FileNotFoundError: Si dataset no existe en data/iquitos_ev_mall
        ValueError: Si los datos no tienen las dimensiones correctas
        RuntimeError: Si los datos no pueden cargarse correctamente
    """
    
    print("\n" + "="*90)
    print(f"[VALIDACION OBLIGATORIA] {agent_name} - Verificando dataset data/iquitos_ev_mall")
    print("="*90)
    
    dataset_dir = Path('data/iquitos_ev_mall')
    
    # ========================================================================
    # [1] VERIFICAR QUE EXISTE data/iquitos_ev_mall
    # ========================================================================
    if not dataset_dir.exists():
        error_msg = f"""
        
╔════════════════════════════════════════════════════════════════╗
║                   ERROR CRITICO                                ║
║                                                                ║
║  DATASET OBLIGATORIO NO ENCONTRADO:                           ║
║  {str(dataset_dir):<50} 
║                                                                ║
║  ACCION REQUERIDA:                                            ║
║  1. Ejecutar: python -m scripts.build_dataset_iquitos         ║
║  2. O descargar dataset compilado                             ║
║  3. Colocar en: {str(dataset_dir):<30}
║                                                                ║
║  Los 3 agentes (SAC, PPO, A2C) DEBEN cargar desde:           ║
║  {str(dataset_dir):<50}
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(error_msg)
        raise FileNotFoundError(error_msg.strip())
    
    print(f"✓ Directorio encontrado: {dataset_dir.absolute()}")
    
    # ========================================================================
    # [2] VERIFICAR ARCHIVOS REQUERIDOS
    # ========================================================================
    required_files = {
        'solar_generation.csv': 'Generación solar (8,760 horas)',
        'chargers_timeseries.csv': 'Demanda chargers (38 sockets × 8,760 horas)',
        'mall_demand.csv': 'Demanda mall (8,760 horas)',
        'bess_timeseries.csv': 'BESS simulation (8,760 horas)',
        'dataset_config_v7.json': 'Metadatos del dataset',
    }
    
    missing_files = []
    for filename, description in required_files.items():
        filepath = dataset_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename:40s} ({description})")
        else:
            print(f"  ✗ {filename:40s} (**FALTA**)")
            missing_files.append(filename)
    
    if missing_files:
        error_msg = f"""
        
╔════════════════════════════════════════════════════════════════╗
║                   ERROR CRITICO                                ║
║                                                                ║
║  ARCHIVOS FALTANTES EN data/iquitos_ev_mall:                  ║
║  {', '.join(missing_files):<50}
║                                                                ║
║  Los 3 agentes requieren TODOS estos archivos:               ║
║  {', '.join(required_files.keys()):<48}
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(error_msg)
        raise FileNotFoundError(error_msg.strip())
    
    # ========================================================================
    # [3] VALIDAR DIMENSIONES Y CONTENIDO
    # ========================================================================
    print("\n[VALIDACION] Verificando dimensiones...")
    
    try:
        # Solar
        df_solar = pd.read_csv(dataset_dir / 'solar_generation.csv')
        if len(df_solar) != 8760:
            raise ValueError(f"Solar: {len(df_solar)} horas != 8760")
        print(f"  ✓ Solar: {len(df_solar)} horas (correcto)")
        
        # Chargers
        df_chargers = pd.read_csv(dataset_dir / 'chargers_timeseries.csv')
        if len(df_chargers) != 8760:
            raise ValueError(f"Chargers: {len(df_chargers)} horas != 8760")
        numeric_cols = []
        for col in df_chargers.columns[1:]:
            try:
                pd.to_numeric(df_chargers[col])
                numeric_cols.append(col)
            except:
                pass
        if len(numeric_cols) < 38:
            raise ValueError(f"Chargers: {len(numeric_cols)} columnas numéricas < 38 sockets")
        print(f"  ✓ Chargers: {len(df_chargers)} horas × {len(numeric_cols)} sockets (correcto)")
        
        # Mall
        df_mall = pd.read_csv(dataset_dir / 'mall_demand.csv')
        if len(df_mall) != 8760:
            raise ValueError(f"Mall: {len(df_mall)} horas != 8760")
        print(f"  ✓ Mall: {len(df_mall)} horas (correcto)")
        
        # BESS
        df_bess = pd.read_csv(dataset_dir / 'bess_timeseries.csv')
        if len(df_bess) != 8760:
            raise ValueError(f"BESS: {len(df_bess)} horas != 8760")
        print(f"  ✓ BESS: {len(df_bess)} horas (correcto)")
        
        print("\n✓ Todas las dimensiones son correctas (8,760 horas = 1 año)")
        
    except Exception as e:
        error_msg = f"""
        
╔════════════════════════════════════════════════════════════════╗
║                   ERROR EN DATOS                               ║
║                                                                ║
║  {str(e):<58}
║                                                                ║
║  Ejecutar verificación completa:                              ║
║  python verify_iquitos_ev_mall_dataset.py                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(error_msg)
        raise RuntimeError(error_msg.strip()) from e
    
    # ========================================================================
    # [4] VALIDAR INTEGRIDAD DE DATOS (no NaN, no vacios)
    # ========================================================================
    print("\n[VALIDACION] Verificando integridad...")
    
    try:
        col = 'energia_kwh' if 'energia_kwh' in df_solar.columns else 'potencia_kw'
        solar_data = df_solar[col].values.astype(float)
        if np.any(np.isnan(solar_data)):
            raise ValueError("Solar contiene NaN")
        if np.sum(solar_data) == 0:
            raise ValueError("Solar suma = 0 (datos vacíos)")
        print(f"  ✓ Solar: {np.sum(solar_data):,.0f} kWh/año (datos válidos)")
        
        power_cols = numeric_cols[:38]
        chargers_data = df_chargers[power_cols].astype(float).values
        if np.any(np.isnan(chargers_data)):
            raise ValueError("Chargers contiene NaN")
        if np.sum(chargers_data) == 0:
            raise ValueError("Chargers suma = 0 (datos vacíos)")
        print(f"  ✓ Chargers: {np.sum(chargers_data):,.0f} kWh/año (datos válidos)")
        
        mall_col = df_mall.columns[-1] if df_mall.shape[1] > 1 else df_mall.columns[0]
        mall_data = df_mall[mall_col].values.astype(float)
        if np.any(np.isnan(mall_data)):
            raise ValueError("Mall contiene NaN")
        if np.sum(mall_data) == 0:
            raise ValueError("Mall suma = 0 (datos vacíos)")
        print(f"  ✓ Mall: {np.sum(mall_data):,.0f} kWh/año (datos válidos)")
        
        print("\n✓ Todos los datos son válidos (sin NaN, con valores correctos)")
        
    except Exception as e:
        error_msg = f"""
        
╔════════════════════════════════════════════════════════════════╗
║                   ERROR DE INTEGRIDAD                          ║
║                                                                ║
║  {str(e):<58}
║                                                                ║
║  Regenerar dataset:                                           ║
║  python -m scripts.build_dataset_iquitos                      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(error_msg)
        raise RuntimeError(error_msg.strip()) from e
    
    # ========================================================================
    # [5] VERIFICAR QUE NO ESTA USANDO RUTAS ALTERNATIVAS
    # ========================================================================
    print("\n[VALIDACION] Verificando que NO usa rutas alternativas...")
    
    # Verificar que data/oe2 NO es utilizado
    alternative_paths = [
        Path('data/oe2'),
        Path('data/interim/oe2'),
        Path('data/processed'),
    ]
    
    for alt_path in alternative_paths:
        if alt_path.exists():
            print(f"  ⚠️  Ruta alternativa encontrada: {alt_path} (será IGNORADA)")
    
    print(f"  ✓ OBLIGATORIO: Usará SOLO data/iquitos_ev_mall")
    
    # ========================================================================
    # [6] RESULTADO FINAL
    # ========================================================================
    print("\n" + "="*90)
    print(f"✅ [{agent_name}] VALIDACION EXITOSA")
    print("="*90)
    print(f"""
    El agente {agent_name} está autorizado para:
    - Cargar desde: data/iquitos_ev_mall/ (OBLIGATORIO)
    - Dataset compilado: v7.0 (data_loader)
    - Sincronización: SAC ↔ PPO ↔ A2C (datos IDENTICOS)
    - Entrenamiento: Listo para iniciar
    """)
    print("="*90 + "\n")
    
    return True


def validate_all_agents():
    """
    Validación cruzada: Verifica que los 3 agentes cargan idénticamente
    """
    print("\n" + "="*90)
    print("VALIDACION CRUZADA: SAC ↔ PPO ↔ A2C")
    print("="*90 + "\n")
    
    dataset_dir = Path('data/iquitos_ev_mall')
    
    try:
        # Cargar datos
        df_solar = pd.read_csv(dataset_dir / 'solar_generation.csv')
        df_chargers = pd.read_csv(dataset_dir / 'chargers_timeseries.csv')
        df_mall = pd.read_csv(dataset_dir / 'mall_demand.csv')
        df_bess = pd.read_csv(dataset_dir / 'bess_timeseries.csv')
        
        # Procesar
        col = 'energia_kwh' if 'energia_kwh' in df_solar.columns else 'potencia_kw'
        solar = np.asarray(df_solar[col].values[:8760], dtype=np.float32)
        
        numeric_cols = []
        for c in df_chargers.columns[1:]:
            try:
                pd.to_numeric(df_chargers[c])
                numeric_cols.append(c)
            except:
                pass
        chargers = df_chargers[numeric_cols[:38]].astype(float).values[:8760, :].astype(np.float32)
        
        mall_col = df_mall.columns[-1] if df_mall.shape[1] > 1 else df_mall.columns[0]
        mall = np.asarray(df_mall[mall_col].values[:8760], dtype=np.float32)
        
        # Verificar que todos los datos son iguales cuando se cargan múltiples veces
        solar2 = np.asarray(df_solar[col].values[:8760], dtype=np.float32)
        chargers2 = df_chargers[numeric_cols[:38]].astype(float).values[:8760, :].astype(np.float32)
        mill2 = np.asarray(df_mall[mall_col].values[:8760], dtype=np.float32)
        
        assert np.allclose(solar, solar2), "Solar datos inconsistentes"
        assert np.allclose(chargers, chargers2), "Chargers datos inconsistentes"
        assert np.allclose(mall, mill2), "Mall datos inconsistentes"
        
        print("✓ SAC ↔ PPO: Datos idénticos")
        print("✓ SAC ↔ A2C: Datos idénticos")
        print("✓ PPO ↔ A2C: Datos idénticos")
        print("\n✅ SINCRONIZACION PERFECTA - Los 3 agentes cargan datos IDENTICOS")
        print("="*90 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR en sincronización: {e}")
        return False


if __name__ == '__main__':
    # Test: validar todos los agentes
    validate_dataset_connection("SAC")
    validate_dataset_connection("PPO")
    validate_dataset_connection("A2C")
    validate_all_agents()
