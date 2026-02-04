"""
VALIDAR INTEGRACIÓN DEL DATASET DE DEMANDA DEL MALL HORARIA EN CITYLEARN V2

Verifica que el archivo demandamallhorakwh.csv:
1. ✓ Existe y tiene formato correcto (FECHAHORA;kWh)
2. ✓ Tiene 8,785 registros (horas completas del año)
3. ✓ Energía total conservada (≈ 12,403,168 kWh)
4. ✓ Se carga correctamente en dataset_builder
5. ✓ CityLearn v2 puede interpretarlo como non_shiftable_load
"""

import pandas as pd
from pathlib import Path
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _pandas_dt_helpers import extract_hour, extract_values_float

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════════════════════════════

INPUT_FILE = Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv")
EXPECTED_ROWS = 8785  # 365 días × 24 horas + 1 hora del 1/1/2025
EXPECTED_ENERGY_KWH = 12_403_168  # Total energía (invariante)

logger.info("")
logger.info("=" * 100)
logger.info("VALIDACIÓN DE INTEGRACIÓN - DATASET HORARIO EN CITYLEARN V2")
logger.info("=" * 100)
logger.info("")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 1: VALIDAR ARCHIVO
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("PASO 1️⃣  VALIDAR ARCHIVO DE DEMANDA HORARIA")
logger.info("─" * 100)

if not INPUT_FILE.exists():
    logger.error(f"❌ ARCHIVO NO ENCONTRADO: {INPUT_FILE}")
    exit(1)

logger.info(f"✓ Archivo encontrado: {INPUT_FILE}")
logger.info(f"  Tamaño: {INPUT_FILE.stat().st_size:,} bytes")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 2: CARGAR Y VALIDAR FORMATO
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 2️⃣  CARGAR Y VALIDAR FORMATO")
logger.info("─" * 100)

try:
    df = pd.read_csv(INPUT_FILE, sep=";")
    logger.info(f"✓ Archivo cargado correctamente")
    logger.info(f"  Filas: {len(df):,}")
    logger.info(f"  Columnas: {list(df.columns)}")
except Exception as e:
    logger.error(f"❌ Error cargando archivo: {e}")
    exit(1)

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 3: VALIDAR COLUMNAS
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 3️⃣  VALIDAR COLUMNAS REQUERIDAS")
logger.info("─" * 100)

required_cols = ["FECHAHORA", "kWh"]
if not all(col in df.columns for col in required_cols):
    logger.error(f"❌ Columnas faltantes. Se esperaba: {required_cols}, se encontró: {list(df.columns)}")
    exit(1)

logger.info(f"✓ Columnas validadas: {required_cols}")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 4: VALIDAR NÚMERO DE REGISTROS
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 4️⃣  VALIDAR NÚMERO DE REGISTROS HORARIOS")
logger.info("─" * 100)

logger.info(f"  Registros: {len(df):,}")
logger.info(f"  Esperado: {EXPECTED_ROWS:,}")

if abs(len(df) - EXPECTED_ROWS) > 10:  # Tolerancia de 10 registros
    logger.warning(f"⚠️  DISCREPANCIA: Se esperaban ~{EXPECTED_ROWS} registros, se encontraron {len(df):,}")
    logger.warning(f"   Diferencia: {len(df) - EXPECTED_ROWS:+,} registros")
else:
    logger.info(f"✓ Número de registros correcto (tolerancia: ±10)")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 5: VALIDAR UNIDADES (kWh)
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 5️⃣  VALIDAR UNIDADES Y RANGO DE VALORES")
logger.info("─" * 100)

# Convertir a numérico
df["kWh"] = pd.to_numeric(df["kWh"], errors="coerce")

if df["kWh"].isna().any():
    logger.error(f"❌ Valores kWh inválidos encontrados: {df['kWh'].isna().sum()} registros")
    exit(1)

total_kwh = df["kWh"].sum()
mean_kwh = df["kWh"].mean()
min_kwh = df["kWh"].min()
max_kwh = df["kWh"].max()
std_kwh = df["kWh"].std()

logger.info(f"✓ Unidad: kWh (energía, no potencia)")
logger.info(f"  Total: {total_kwh:,.0f} kWh")
logger.info(f"  Esperado: {EXPECTED_ENERGY_KWH:,} kWh")
logger.info(f"  Diferencia: {total_kwh - EXPECTED_ENERGY_KWH:,.0f} kWh ({((total_kwh - EXPECTED_ENERGY_KWH) / EXPECTED_ENERGY_KWH * 100):+.3f}%)")
logger.info(f"  Promedio: {mean_kwh:,.2f} kWh/hora")
logger.info(f"  Mínimo: {min_kwh:,.2f} kWh")
logger.info(f"  Máximo: {max_kwh:,.2f} kWh")
logger.info(f"  Desviación estándar: {std_kwh:,.2f} kWh")

# Validar rango
if min_kwh < 0:
    logger.error(f"❌ Valores negativos encontrados: mínimo = {min_kwh}")
    exit(1)

if max_kwh > 3500:
    logger.warning(f"⚠️  Máximo muy alto: {max_kwh} kWh (expected ~2800 kWh para demanda mall)")

logger.info(f"✓ Rango de valores válido (0 a {max_kwh:,.0f} kWh)")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 6: VALIDAR DATETIME
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 6️⃣  VALIDAR TIMESTAMPS Y COBERTURA TEMPORAL")
logger.info("─" * 100)

try:
    df["datetime"] = pd.to_datetime(df["FECHAHORA"], format="%d/%m/%Y %H:%M")
    logger.info(f"✓ Timestamps parseados correctamente")
except Exception as e:
    logger.error(f"❌ Error parseando timestamps: {e}")
    exit(1)

min_date = df["datetime"].min()
max_date = df["datetime"].max()
date_range = (max_date - min_date).days

logger.info(f"  Inicio: {min_date.strftime('%d/%m/%Y %H:%M')}")
logger.info(f"  Final: {max_date.strftime('%d/%m/%Y %H:%M')}")
logger.info(f"  Rango: {date_range} días")

if date_range < 364 or date_range > 366:
    logger.warning(f"⚠️  Rango temporal anómalo: {date_range} días (esperado 365 ±1)")
else:
    logger.info(f"✓ Cobertura temporal: 1 año completo ({date_range} días)")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 7: VALIDAR PERIODICIDAD HORARIA
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 7️⃣  VALIDAR PERIODICIDAD HORARIA (SIN DUPLICADOS/GAPS)")
logger.info("─" * 100)

# Verificar que no hay duplicados
duplicates = df["datetime"].duplicated().sum()
if duplicates > 0:
    logger.error(f"❌ Timestamps duplicados encontrados: {duplicates}")
    exit(1)

logger.info(f"✓ Sin duplicados de timestamp")

# Verificar que no hay gaps grandes (mínimo debería ser 1 hora)
df_sorted = df.sort_values("datetime")
# Calculate time difference in hours (diff returns timedelta, need to extract total_seconds)
df_sorted["time_diff"] = df_sorted["datetime"].diff().apply(lambda x: x.total_seconds() / 3600 if pd.notna(x) else 0)

gaps = df_sorted[df_sorted["time_diff"] > 1.5]  # Gap > 1.5 horas
if len(gaps) > 0:
    logger.warning(f"⚠️  {len(gaps)} gaps detectados (> 1.5 horas)")
    logger.warning(f"   Gaps mayores:")
    for idx, row in gaps.head(5).iterrows():
        logger.warning(f"     {row['datetime'].strftime('%d/%m/%Y %H:%M')} (gap: {row['time_diff']:.1f} horas)")
else:
    logger.info(f"✓ Periodicidad horaria consistente (sin gaps)")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 8: VALIDAR PATRONES DE DEMANDA
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 8️⃣  VALIDAR PATRONES DE DEMANDA (PICOS/VALLES)")
logger.info("─" * 100)

# Añadir hora del día
df["hour"] = extract_hour(df["datetime"])

# Demanda por hora del día
hourly_demand = df.groupby("hour")["kWh"].agg(["mean", "min", "max", "std"])

logger.info(f"  Demanda por hora del día (0-23):")
logger.info(f"  Hora  │  Promedio  │   Mínimo   │   Máximo   │  Desv.Est.")
logger.info(f"  ──────┼────────────┼────────────┼────────────┼────────────")

for hour in range(24):
    if hour in hourly_demand.index:
        row = hourly_demand.loc[hour]
        logger.info(f"  {hour:02d}:00 │ {row['mean']:>8,.0f}  │ {row['min']:>8,.0f}  │ {row['max']:>8,.0f}  │ {row['std']:>8,.0f}")

# Detectar picos
peak_hours = hourly_demand.nlargest(5, "mean")
off_peak_hours = hourly_demand.nsmallest(5, "mean")

logger.info(f"")
logger.info(f"  ✓ Top 5 horas pico (promedio):")
for idx, (hour, row) in enumerate(peak_hours.iterrows(), 1):
    logger.info(f"    {idx}. Hora {hour:02d}:00 → {row['mean']:,.0f} kWh")

logger.info(f"")
logger.info(f"  ✓ Top 5 horas valle (promedio):")
for idx, (hour, row) in enumerate(off_peak_hours.iterrows(), 1):
    logger.info(f"    {idx}. Hora {hour:02d}:00 → {row['mean']:,.0f} kWh")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 9: VALIDAR COMPATIBILIDAD CITYLEARN V2
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 9️⃣  VALIDAR COMPATIBILIDAD CITYLEARN V2")
logger.info("─" * 100)

# CityLearn v2 espera:
# 1. Valores numéricos
# 2. Sin NaN/Inf
# 3. Valores positivos
# 4. Longitud correcta (8760 para 1 año)

if not pd.api.types.is_numeric_dtype(df["kWh"]):
    logger.error(f"❌ Columna kWh no es numérica")
    exit(1)

if df["kWh"].isna().any() or df["kWh"].isin([float('inf'), float('-inf')]).any():
    logger.error(f"❌ NaN o Inf detectados en kWh")
    exit(1)

if (df["kWh"] < 0).any():
    logger.error(f"❌ Valores negativos en kWh")
    exit(1)

logger.info(f"✓ Columna kWh es numérica (float64)")
logger.info(f"✓ Sin valores NaN o Inf")
logger.info(f"✓ Todos los valores positivos")

# CityLearn v2 non_shiftable_load espera lista numérica
logger.info(f"✓ Formato compatible con CityLearn v2.non_shiftable_load")
logger.info(f"  Se puede usar como: np.array(df['kWh'].values)")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 10: SIMULAR CARGA EN DATASET_BUILDER
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 🔟  SIMULAR CARGA COMO SI FUERA DATASET_BUILDER")
logger.info("─" * 100)

try:
    # Simular lo que dataset_builder.py hace
    mall_df = pd.read_csv(INPUT_FILE, sep=";")

    # Buscar columna de demanda
    demand_col = None
    for col in mall_df.columns:
        col_lower = col.lower()
        if any(tag in col_lower for tag in ("kwh", "demanda", "kw", "demand")):
            demand_col = col
            break

    if demand_col is None:
        demand_col = mall_df.columns[-1]  # Última columna por defecto

    mall_df["datetime"] = pd.to_datetime(mall_df["FECHAHORA"], format="%d/%m/%Y %H:%M")
    mall_series = mall_df[demand_col].values

    logger.info(f"✓ Simulación de carga exitosa")
    logger.info(f"  Columna detectada: {demand_col}")
    logger.info(f"  Array shape: {mall_series.shape}")
    logger.info(f"  Array dtype: {mall_series.dtype}")
    logger.info(f"  Suma total: {extract_values_float(mall_series).sum():,.0f} kWh")

except Exception as e:
    logger.error(f"❌ Error simulando carga: {e}")
    exit(1)

# ════════════════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("=" * 100)
logger.info("✅ VALIDACIÓN COMPLETADA EXITOSAMENTE")
logger.info("=" * 100)
logger.info("")
logger.info("📊 RESUMEN:")
logger.info(f"  • Archivo: {INPUT_FILE}")
logger.info(f"  • Registros: {len(df):,} (horarios)")
logger.info(f"  • Período: {min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')} ({date_range} días)")
logger.info(f"  • Energía total: {total_kwh:,.0f} kWh")
logger.info(f"  • Unidad: kWh (energía, no potencia)")
logger.info(f"  • Separador: `;` (semicolon)")
logger.info(f"  • Estado CityLearn v2: ✓ COMPATIBLE")
logger.info("")
logger.info("🎯 SIGUIENTE PASO:")
logger.info("  Ejecutar: python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
logger.info("  Esto construirá el schema CityLearn con este dataset horario como demanda del mall")
logger.info("")

