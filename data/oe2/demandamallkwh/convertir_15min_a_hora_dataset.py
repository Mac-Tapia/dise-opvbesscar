#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRANSFORMACIÓN DE DATASETS MALL + SOLAR PARA OE3
════════════════════════════════════════════════════════════════════════════════

DATASET 1: MALL (15 MIN → HORAS + OBSERVABLES CON TARIFA + COSTO)
──────────────────────────────────────────────────────────────────
Entrada: data/oe2/demandamallkwh/demandamallkwh.csv (35,136 registros × 15min)
Salida: data/oe2/demandamallkwh/demandamallhorakwh.csv (8,760 registros × 1h)

ÍNDICE: datetime (fecha + hora como índice)

COLUMNAS OBSERVABLES (5):
├─ mall_demand_kwh: Demanda horaria sin control (suma 4×15min)
├─ mall_co2_indirect_kg: Emisión indirecta (demanda × 0.4521 kg CO2/kWh)
├─ is_hora_punta: 1 si 18:00-23:00 (HP), 0 si resto (HFP)
├─ tarifa_soles_kwh: Tarifa OSINERGMIN según HP/HFP
└─ mall_cost_soles: Costo real (demanda × tarifa)

Tarifas OSINERGMIN Clientes BT5A (Iquitos 2024):
├─ Hora Punta (18:00-23:00): 0.50 S/kWh
└─ Hora Fuera Punta (resto): 0.30 S/kWh

Con esta estructura se puede evaluar:
✓ Cuánto se está reduciendo el costo con control
✓ Cuánto se reduce emisión de CO2
✓ Diferencia de costos entre HP y HFP

DATASET 2: SOLAR (LIMPIEZA)
────────────────────────────
Eliminadas columnas: co2_evitado_mall_kg, co2_evitado_ev_kg
(Razón: SOLAR no evita CO2 directamente; BESS sí)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# ════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ════════════════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Rutas
MALL_DIR = Path(__file__).parent
MALL_INPUT = MALL_DIR / "demandamall15kwh" / "demandamallkwh.csv"
MALL_OUTPUT = MALL_DIR / "demandamallhorakwh.csv"

SOLAR_DIR = MALL_DIR.parent / "solar"
SOLAR_INPUT = SOLAR_DIR / "pv_generation_timeseries.csv"
SOLAR_OUTPUT = SOLAR_DIR / "pv_generation_timeseries_clean.csv"

# Constantes
CO2_FACTOR_KG_KWH = 0.4521  # Factor emisión Iquitos (grid térmico)
TARIFA_HP_SOLES_KWH = 0.50  # Hora Punta (18:00-23:00)
TARIFA_HFP_SOLES_KWH = 0.30  # Hora Fuera Punta (resto)
HP_START_HORA = 18
HP_END_HORA = 23


# ════════════════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ════════════════════════════════════════════════════════════════════════════════════════

def is_hora_punta(hour: int) -> int:
    """Determina si una hora es Hora Punta (1) o Fuera de Punta (0)."""
    return 1 if HP_START_HORA <= hour < HP_END_HORA else 0


def get_tarifa(hour: int) -> float:
    """Retorna la tarifa según OSINERGMIN BT5A."""
    return TARIFA_HP_SOLES_KWH if is_hora_punta(hour) else TARIFA_HFP_SOLES_KWH


# ════════════════════════════════════════════════════════════════════════════════════════
# FASE 1: TRANSFORMACIÓN DE MALL
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("=" * 100)
logger.info("TRANSFORMACIÓN OE3: MALL + SOLAR")
logger.info("=" * 100)
logger.info("")
logger.info("FASE 1️⃣  TRANSFORMACIÓN MALL (15 MIN → HORAS + TARIFAS + COSTOS)")
logger.info("─" * 100)

# --- Validar entrada
if not MALL_INPUT.exists():
    logger.error(f"❌ No encontrado: {MALL_INPUT}")
    sys.exit(1)

logger.info(f"✅ Entrada: {MALL_INPUT}")

# --- Cargar datos
try:
    df_15min = pd.read_csv(MALL_INPUT, sep=';')
    logger.info(f"✅ Cargado: {len(df_15min):,} registros × 15min")
except Exception as e:
    logger.error(f"❌ Error: {e}")
    sys.exit(1)

# --- Validaciones
if not all(col in df_15min.columns for col in ['FECHAHORA', 'kWh']):
    logger.error(f"❌ Columnas faltantes. Disponibles: {list(df_15min.columns)}")
    sys.exit(1)

logger.info(f"✅ Estructura validada")
kwh_total_15min = df_15min['kWh'].sum()
logger.info(f"   Energía total: {kwh_total_15min:,.0f} kWh")

# --- Parsear datetime
try:
    df_15min['datetime'] = pd.to_datetime(df_15min['FECHAHORA'], format='%d/%m/%Y %H:%M')
except Exception as e:
    logger.error(f"❌ Error parsing datetime: {e}")
    sys.exit(1)

df_15min['fecha'] = df_15min['datetime'].dt.date
df_15min['hora'] = df_15min['datetime'].dt.hour

logger.info(f"   Rango: {df_15min['datetime'].min()} a {df_15min['datetime'].max()}")

# --- Agrupar por hora
df_hourly = df_15min.groupby(['fecha', 'hora']).agg({'kWh': 'sum'}).reset_index()
df_hourly.columns = ['fecha', 'hora', 'mall_demand_kwh']
df_hourly = df_hourly.sort_values(['fecha', 'hora']).reset_index(drop=True)

logger.info(f"✅ Agrupado: {len(df_hourly):,} horas")
logger.info(f"   Energía preservada: {df_hourly['mall_demand_kwh'].sum():,.0f} kWh")
logger.info(f"   Diferencia: {abs(kwh_total_15min - df_hourly['mall_demand_kwh'].sum()):.2f} kWh")

# --- Crear datetime completo
df_hourly['datetime'] = pd.to_datetime(
    df_hourly['fecha'].astype(str) + ' ' +
    df_hourly['hora'].astype(str).str.zfill(2) + ':00',
    format='%Y-%m-%d %H:%M'
)

# --- Crear observables
df_hourly['mall_co2_indirect_kg'] = df_hourly['mall_demand_kwh'] * CO2_FACTOR_KG_KWH
df_hourly['is_hora_punta'] = df_hourly['hora'].apply(is_hora_punta)
df_hourly['tarifa_soles_kwh'] = df_hourly['hora'].apply(get_tarifa)
df_hourly['mall_cost_soles'] = df_hourly['mall_demand_kwh'] * df_hourly['tarifa_soles_kwh']

logger.info(f"✅ Observables creados:")
logger.info(f"   ├─ mall_demand_kwh: {df_hourly['mall_demand_kwh'].sum():,.0f} kWh")
logger.info(f"   ├─ mall_co2_indirect_kg: {df_hourly['mall_co2_indirect_kg'].sum():,.0f} kg CO2")
logger.info(f"   ├─ is_hora_punta: {df_hourly['is_hora_punta'].sum():.0f} horas HP")
logger.info(f"   └─ mall_cost_soles: S/ {df_hourly['mall_cost_soles'].sum():,.2f}")

hp_energy = df_hourly[df_hourly['is_hora_punta'] == 1]['mall_demand_kwh'].sum()
hp_cost = df_hourly[df_hourly['is_hora_punta'] == 1]['mall_cost_soles'].sum()
hfp_energy = df_hourly[df_hourly['is_hora_punta'] == 0]['mall_demand_kwh'].sum()
hfp_cost = df_hourly[df_hourly['is_hora_punta'] == 0]['mall_cost_soles'].sum()

logger.info(f"")
logger.info(f"✅ Análisis por tarifa:")
logger.info(f"   HP (18-23)   @ S/ {TARIFA_HP_SOLES_KWH:5.2f}/kWh: {hp_energy:>10,.0f} kWh → S/ {hp_cost:>12,.2f}")
logger.info(f"   HFP (resto)  @ S/ {TARIFA_HFP_SOLES_KWH:5.2f}/kWh: {hfp_energy:>10,.0f} kWh → S/ {hfp_cost:>12,.2f}")
logger.info(f"   ───────────────────────────────────────────────────────────────")
logger.info(f"   Total año:                              S/ {df_hourly['mall_cost_soles'].sum():>12,.2f}")

# --- Armar dataset final con datetime como índice
df_mall_final = df_hourly[
    ['datetime', 'mall_demand_kwh', 'mall_co2_indirect_kg', 
     'is_hora_punta', 'tarifa_soles_kwh', 'mall_cost_soles']
].copy()
df_mall_final = df_mall_final.set_index('datetime')

logger.info(f"✅ Dataset final con índice datetime:")
logger.info(f"   Registros: {len(df_mall_final):,}")
logger.info(f"   Columnas: {list(df_mall_final.columns)}")

# --- Guardar MALL
MALL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
try:
    df_mall_final.to_csv(MALL_OUTPUT, sep=',')
    logger.info(f"✅ Guardado: {MALL_OUTPUT}")
    logger.info(f"   Tamaño: {MALL_OUTPUT.stat().st_size / 1e3:.1f} KB")
except Exception as e:
    logger.error(f"❌ Error guardando: {e}")
    sys.exit(1)

# --- Verificación
try:
    df_check = pd.read_csv(MALL_OUTPUT, index_col=0, parse_dates=True)
    logger.info(f"✅ Verificación OK: {len(df_check):,} registros")
except Exception as e:
    logger.error(f"❌ Error verificando: {e}")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════════════════
# FASE 2: LIMPIEZA DE SOLAR
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("FASE 2️⃣  LIMPIEZA SOLAR (REMOVER COLUMNAS CO2 INAPLICABLES)")
logger.info("─" * 100)

if not SOLAR_INPUT.exists():
    logger.warning(f"⚠️  No encontrado: {SOLAR_INPUT}")
    logger.warning(f"    Saltando limpieza SOLAR")
else:
    logger.info(f"✅ Entrada: {SOLAR_INPUT}")

    try:
        df_solar = pd.read_csv(SOLAR_INPUT)
        logger.info(f"✅ Cargado: {len(df_solar):,} registros")
        logger.info(f"   Columnas: {list(df_solar.columns)}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

    # Remover columnas CO2 no aplicables
    cols_to_remove = ['co2_evitado_mall_kg', 'co2_evitado_ev_kg']
    cols_removed = [c for c in cols_to_remove if c in df_solar.columns]

    if cols_removed:
        df_solar = df_solar.drop(columns=cols_removed)
        logger.info(f"✅ Removidas: {', '.join(cols_removed)}")
    else:
        logger.info(f"ℹ️  Sin columnas CO2 para remover")

    logger.info(f"   Columnas finales: {list(df_solar.columns)}")

    # Guardar SOLAR limpio
    SOLAR_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        df_solar.to_csv(SOLAR_OUTPUT, index=False)
        logger.info(f"✅ Guardado: {SOLAR_OUTPUT}")
        logger.info(f"   Tamaño: {SOLAR_OUTPUT.stat().st_size / 1e3:.1f} KB")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("=" * 100)
logger.info("✅ TRANSFORMACIÓN COMPLETADA")
logger.info("=" * 100)
logger.info("")
logger.info("📊 RESUMEN FINAL:")
logger.info("")
logger.info("MALL:")
logger.info(f"  Entrada:  {MALL_INPUT} (35,136 × 15min)")
logger.info(f"  Salida:   {MALL_OUTPUT} (8,760 × 1h)")
logger.info(f"  Índice:   datetime (fecha + hora como índice)")
logger.info(f"  Columnas: mall_demand_kwh, mall_co2_indirect_kg, is_hora_punta,")
logger.info(f"            tarifa_soles_kwh, mall_cost_soles")
logger.info("")
logger.info("TARIFAS OSINERGMIN BT5A:")
logger.info(f"  HP (18:00-23:00):  S/ {TARIFA_HP_SOLES_KWH}/kWh")
logger.info(f"  HFP (resto):       S/ {TARIFA_HFP_SOLES_KWH}/kWh")
logger.info("")
logger.info("FACTORES:")
logger.info(f"  CO2 factor:        {CO2_FACTOR_KG_KWH} kg CO2/kWh")
logger.info("")
if SOLAR_INPUT.exists():
    logger.info("SOLAR:")
    logger.info(f"  Entrada:  {SOLAR_INPUT}")
    logger.info(f"  Salida:   {SOLAR_OUTPUT}")
    logger.info(f"  Acción:   Removidas columnas CO2 inaplicables")
logger.info("")
logger.info("=" * 100)
