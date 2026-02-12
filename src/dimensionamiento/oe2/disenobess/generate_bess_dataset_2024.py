#!/usr/bin/env python
"""
Script para ejecutar BESS y generar dataset horario 2024 con DatetimeIndex.

Integra:
- PV: pv_generation_timeseries.csv (8,760 horas)
- EV: chargers_real_hourly_2024.csv (8,760 horas, 38 sockets)
- Mall: demandamallhorakwh.csv (horario)

Salida: data/oe2/bess/bess_hourly_dataset_2024.csv
- Índice: DatetimeIndex 2024 (horario, UTC-5)
- 8,760 filas × N columnas (simulación BESS)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))


def load_pv_2024() -> pd.DataFrame:
    """Carga generación PV 2024 desde pv_generation_timeseries.csv"""
    pv_path = workspace_root / "data/oe2/Generacionsolar/pv_generation_timeseries.csv"

    logger.info(f"\n📂 Cargando PV: {pv_path.name}")
    df = pd.read_csv(pv_path)

    # Debe tener 8,760 filas (1 año)
    if len(df) != 8760:
        logger.error(f"❌ PV tiene {len(df)} filas, se esperan 8,760")
        raise ValueError(f"PV dataset incompleto: {len(df)} filas")

    # Asegurar que 'pv_kwh' existe
    if 'pv_kwh' not in df.columns:
        logger.error(f"❌ Columna 'pv_kwh' no encontrada. Columnas: {df.columns.tolist()}")
        raise ValueError("Columna 'pv_kwh' no encontrada en PV dataset")

    logger.info(f"   ✅ Shape: {df.shape}")
    logger.info(f"   ✅ PV anual: {df['pv_kwh'].sum():,.0f} kWh")

    return df[['pv_kwh']].copy()


def load_ev_2024() -> pd.DataFrame:
    """Carga demanda EV 2024 desde chargers_real_hourly_2024.csv"""
    ev_path = workspace_root / "data/oe2/chargers/chargers_real_hourly_2024.csv"

    logger.info(f"\n📂 Cargando EV: {ev_path.name}")
    df = pd.read_csv(ev_path, index_col=0)

    # Debe tener 8,760 filas y 38 columnas
    if df.shape != (8760, 38):
        logger.error(f"❌ EV tiene shape {df.shape}, se esperan (8760, 38)")
        raise ValueError(f"EV dataset incorrecto: shape {df.shape}")

    # Sumar todas las columnas para obtener demanda EV total por hora
    ev_total = df.sum(axis=1).reset_index(drop=True)

    logger.info(f"   ✅ Shape: {df.shape} → Sumadas: ({len(ev_total)},)")
    logger.info(f"   ✅ EV anual: {ev_total.sum():,.0f} kWh")
    logger.info(f"   ✅ Sockets: {df.shape[1]} (30 motos + 8 mototaxis)")

    return pd.DataFrame({'ev_kwh': ev_total})


def load_mall_2024() -> pd.DataFrame:
    """Carga demanda del mall 2024 desde demandamallhorakwh.csv"""
    mall_path = workspace_root / "data/oe2/demandamallkwh/demandamallhorakwh.csv"

    logger.info(f"\n📂 Cargando Mall: {mall_path.name}")

    # Leer con separador correcto
    df = pd.read_csv(mall_path, sep=";")

    # Renombrar columnas
    df.columns = ['fechahora', 'kwh']
    df['fechahora'] = pd.to_datetime(df['fechahora'], format='%d/%m/%Y %H:%M', dayfirst=True)

    # Filtrar para 2024 exactamente (8,760 horas)
    df_2024 = df[df['fechahora'].dt.year == 2024].copy()
    df_2024 = df_2024.sort_values('fechahora').reset_index(drop=True)

    # Asegurar exactamente 8,760 filas
    if len(df_2024) > 8760:
        df_2024 = df_2024.iloc[:8760]  # Tomar primeras 8,760
        logger.warning(f"   ⚠️  Truncado a 8,760 horas (tenía {len(df_2024)})")
    elif len(df_2024) < 8760:
        logger.error(f"❌ Mall tiene {len(df_2024)} horas, se esperan 8,760")
        raise ValueError(f"Mall dataset incompleto: {len(df_2024)} horas")

    # Crear output
    mall_kwh = df_2024['kwh'].values

    logger.info(f"   ✅ Shape: {mall_kwh.shape}")
    logger.info(f"   ✅ Mall anual: {mall_kwh.sum():,.0f} kWh")
    logger.info(f"   ✅ Período: {df_2024['fechahora'].min()} a {df_2024['fechahora'].max()}")

    return pd.DataFrame({'mall_kwh': mall_kwh})


def simulate_bess_simple(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float = 940.0,   # v5.2: 940 kWh
    power_kw: float = 342.0,       # v5.2: 342 kW
    dod: float = 0.80,
    efficiency: float = 0.95,
    initial_soc: float = 0.50,
) -> pd.DataFrame:
    """
    Simula operación del BESS hora a hora (simple pero realista).

    Prioridad:
    1. Solar → EV (primero)
    2. Excedente solar → Carga BESS
    3. Excedente final → Mall y red
    4. BESS descarga cuando solar no cubre EV (18h-22h)

    Returns:
        DataFrame con:
        - pv_kwh: Generación solar
        - ev_kwh: Demanda EV
        - mall_kwh: Demanda mall
        - pv_to_ev: Solar usado por EV
        - pv_to_bess: Solar usado por BESS
        - pv_to_mall: Solar usado por mall
        - grid_to_ev: Red usado por EV
        - grid_to_mall: Red usado por mall
        - bess_charge: Carga del BESS
        - bess_discharge: Descarga del BESS
        - soc_percent: Estado de carga (%)
    """
    n = len(pv_kwh)
    hours = np.arange(n) % 24

    # Parámetros SOC
    soc_min = 1.0 - dod
    soc_max = 1.0
    current_soc = initial_soc
    soc_array = np.zeros(n)

    # Arrays de salida
    pv_to_ev = np.zeros(n)
    pv_to_bess = np.zeros(n)
    pv_to_mall = np.zeros(n)
    grid_to_ev = np.zeros(n)
    grid_to_mall = np.zeros(n)
    bess_charge = np.zeros(n)
    bess_discharge = np.zeros(n)
    soc_array = np.zeros(n)

    for i in range(n):
        h = hours[i]

        # PASO 1: Solar → EV (prioridad máxima)
        pv_to_ev[i] = min(pv_kwh[i], ev_kwh[i])

        # PASO 2: Excedente solar
        pv_available = pv_kwh[i] - pv_to_ev[i]

        # PASO 3: Carga BESS durante pico solar (5-17h) si hay excedente
        if (5 <= h <= 17) and pv_available > 0.1:
            # Carga BESS limitada por potencia
            charge_available = power_kw * efficiency  # kWh/h
            max_charge = (soc_max - current_soc) * capacity_kwh
            bess_charge[i] = min(pv_available, charge_available, max_charge)
            pv_to_bess[i] = bess_charge[i]
            current_soc += bess_charge[i] / capacity_kwh

            # Resto a mall
            pv_to_mall[i] = pv_available - pv_to_bess[i]
        else:
            pv_to_mall[i] = pv_available

        # PASO 4: EV deficit
        ev_deficit = ev_kwh[i] - pv_to_ev[i]

        # PASO 5: BESS descarga (18h-22h) cuando hay deficit EV
        if (18 <= h <= 22) and ev_deficit > 0.1 and current_soc > soc_min:
            # Descarga BESS limitada por potencia
            discharge_available = power_kw * efficiency  # kWh/h
            max_discharge = (current_soc - soc_min) * capacity_kwh
            bess_discharge[i] = min(ev_deficit, discharge_available, max_discharge)
            grid_to_ev[i] = max(0, ev_deficit - bess_discharge[i])
            current_soc -= bess_discharge[i] / capacity_kwh
        else:
            # Sin descarga BESS, EV va directamente a red
            grid_to_ev[i] = ev_deficit

        # PASO 6: Mall deficit (después de PV y BESS)
        mall_deficit = mall_kwh[i] - pv_to_mall[i]
        grid_to_mall[i] = max(0, mall_deficit)

        # Actualizar SOC
        soc_array[i] = current_soc

    # Retornar DataFrame
    return pd.DataFrame({
        'pv_kwh': pv_kwh,
        'ev_kwh': ev_kwh,
        'mall_kwh': mall_kwh,
        'pv_to_ev_kwh': pv_to_ev,
        'pv_to_bess_kwh': pv_to_bess,
        'pv_to_mall_kwh': pv_to_mall,
        'grid_to_ev_kwh': grid_to_ev,
        'grid_to_mall_kwh': grid_to_mall,
        'bess_charge_kwh': bess_charge,
        'bess_discharge_kwh': bess_discharge,
        'soc_percent': soc_array * 100,
    })


def main():
    """Ejecutar simulación BESS y generar dataset 2024."""

    logger.info("\n" + "="*80)
    logger.info("GENERACIÓN DE DATASET BESS HORARIO 2024")
    logger.info("="*80)

    # ========================================================================
    # CARGAR DATOS
    # ========================================================================

    try:
        df_pv = load_pv_2024()
        df_ev = load_ev_2024()
        df_mall = load_mall_2024()
    except Exception as e:
        logger.error(f"❌ Error cargando datos: {e}")
        return 1

    # ========================================================================
    # SIMULAR BESS
    # ========================================================================

    logger.info(f"\n🚀 Simulando BESS...")

    try:
        df_bess = simulate_bess_simple(
            pv_kwh=df_pv['pv_kwh'].values,
            ev_kwh=df_ev['ev_kwh'].values,
            mall_kwh=df_mall['mall_kwh'].values,
            capacity_kwh=940.0,   # v5.2: 940 kWh (100% cobertura EV)
            power_kw=342.0,       # v5.2: 342 kW
            dod=0.80,             # 80% DoD
            efficiency=0.95,      # 95% eficiencia
            initial_soc=0.50,     # 50% SOC inicial
        )

        logger.info(f"   ✅ BESS simulado exitosamente")
        logger.info(f"   Columnas: {', '.join(df_bess.columns.tolist())}")

    except Exception as e:
        logger.error(f"❌ Error simulando BESS: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ========================================================================
    # CREAR ÍNDICE DATETIME 2024
    # ========================================================================

    logger.info(f"\n📅 Creando índice temporal 2024...")

    date_index = pd.date_range(
        start="2024-01-01 00:00:00",
        periods=8760,
        freq="h",
        tz="America/Lima"  # UTC-5
    )

    logger.info(f"   ✅ Inicio: {date_index[0]}")
    logger.info(f"   ✅ Fin: {date_index[-1]}")
    logger.info(f"   ✅ Períodos: {len(date_index)}")
    logger.info(f"   ✅ Frecuencia: {date_index.freq}")

    # Asignar índice
    df_bess.index = date_index
    df_bess.index.name = "datetime"

    # ========================================================================
    # GUARDAR CSV
    # ========================================================================

    logger.info(f"\n💾 Guardando dataset...")

    bess_dir = workspace_root / "data/oe2/bess"
    bess_dir.mkdir(parents=True, exist_ok=True)

    output_csv = bess_dir / "bess_hourly_dataset_2024.csv"
    df_bess.to_csv(output_csv)

    file_size_mb = output_csv.stat().st_size / (1024 * 1024)
    logger.info(f"   ✅ Guardado: {output_csv}")
    logger.info(f"   📦 Tamaño: {file_size_mb:.1f} MB")

    # ========================================================================
    # VALIDACIÓN Y RESUMEN
    # ========================================================================

    logger.info(f"\n✅ DATASET GENERADO EXITOSAMENTE")
    logger.info(f"\n📋 RESUMEN:")
    logger.info(f"   Archivo: bess_hourly_dataset_2024.csv")
    logger.info(f"   Ubicación: {bess_dir}")
    logger.info(f"   Dimensiones: {df_bess.shape[0]} filas × {df_bess.shape[1]} columnas")
    logger.info(f"   Índice: DatetimeIndex (2024-01-01 a 2024-12-31, horario, UTC-5)")

    logger.info(f"\n📊 ESTADÍSTICAS ANUALES:")
    logger.info(f"   PV generado: {df_bess['pv_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   EV demanda: {df_bess['ev_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Mall demanda: {df_bess['mall_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Total demanda: {(df_bess['ev_kwh'].sum() + df_bess['mall_kwh'].sum()):>12,.0f} kWh")

    logger.info(f"\n⚡ BALANCE ENERGÉTICO:")
    logger.info(f"   PV → EV: {df_bess['pv_to_ev_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   PV → BESS: {df_bess['pv_to_bess_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   PV → Mall: {df_bess['pv_to_mall_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Red → EV: {df_bess['grid_to_ev_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Red → Mall: {df_bess['grid_to_mall_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Total red: {(df_bess['grid_to_ev_kwh'].sum() + df_bess['grid_to_mall_kwh'].sum()):>12,.0f} kWh")

    logger.info(f"\n🔋 BESS OPERACIÓN:")
    logger.info(f"   Carga anual: {df_bess['bess_charge_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   Descarga anual: {df_bess['bess_discharge_kwh'].sum():>12,.0f} kWh")
    logger.info(f"   SOC mínimo: {df_bess['soc_percent'].min():>12.1f}%")
    logger.info(f"   SOC máximo: {df_bess['soc_percent'].max():>12.1f}%")
    logger.info(f"   SOC promedio: {df_bess['soc_percent'].mean():>12.1f}%")

    logger.info(f"\n🎯 AUTOSUFICIENCIA:")
    total_load = df_bess['ev_kwh'].sum() + df_bess['mall_kwh'].sum()
    pv_coverage = df_bess['pv_to_ev_kwh'].sum() + df_bess['pv_to_mall_kwh'].sum()
    bess_contribution = df_bess['bess_discharge_kwh'].sum()
    self_sufficiency = (pv_coverage + bess_contribution) / total_load * 100

    logger.info(f"   Solar cubre: {pv_coverage/total_load*100:>11.1f}% de demanda")
    logger.info(f"   BESS cubre: {bess_contribution/total_load*100:>12.1f}% de demanda")
    logger.info(f"   Total autosuficiencia: {self_sufficiency:>4.1f}%")
    logger.info(f"   Red requerida: {100-self_sufficiency:>12.1f}%")

    # ========================================================================
    # VERIFICACIÓN
    # ========================================================================

    logger.info(f"\n✅ VERIFICACIÓN DE INTEGRIDAD:")

    # 8,760 filas
    assert len(df_bess) == 8760, f"Error: {len(df_bess)} filas vs 8,760 esperado"
    logger.info(f"   ✅ 8,760 filas (1 año completo)")

    # Índice único
    assert df_bess.index.is_unique, "Error: Índice duplicado"
    logger.info(f"   ✅ Índice único")

    # Sin NaN
    assert not df_bess.isna().any().any(), "Error: Valores NaN encontrados"
    logger.info(f"   ✅ Sin valores NaN")

    # Año 2024
    assert df_bess.index[0].year == 2024, "Error: Año incorrecto"
    logger.info(f"   ✅ Año 2024 validado")

    # Primeras y últimas filas
    logger.info(f"\n📖 PRIMERAS 5 FILAS:")
    for idx, row in df_bess.head(5).iterrows():
        logger.info(f"   {idx.strftime('%Y-%m-%d %H:%M')}: PV={row['pv_kwh']:>6.1f} | EV={row['ev_kwh']:>6.1f} | SOC={row['soc_percent']:>5.1f}%")

    logger.info(f"\n📖 ÚLTIMAS 5 FILAS:")
    for idx, row in df_bess.tail(5).iterrows():
        logger.info(f"   {idx.strftime('%Y-%m-%d %H:%M')}: PV={row['pv_kwh']:>6.1f} | EV={row['ev_kwh']:>6.1f} | SOC={row['soc_percent']:>5.1f}%")

    logger.info(f"\n" + "="*80)
    logger.info(f"✅ PROCESO COMPLETADO EXITOSAMENTE")
    logger.info(f"="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
