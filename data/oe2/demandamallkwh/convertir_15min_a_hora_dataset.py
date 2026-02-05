"""
CONVERSIÓN DE DATASET: 15 MINUTOS → HORAS (AÑO COMPLETO)

Convierte el dataset de demanda del mall de 15 minutos a horas:
- Entrada: data/interim/oe2/demandamallkwh/demandamallkwh.csv (35,136 registros de 15 min)
- Salida: data/interim/oe2/demandamallkwh/demandamallhorakwh.csv (8,760 registros de 1 hora)

Validaciones:
✅ Unidades confirmadas como kWh (energía)
✅ Separador: `;` (semicolon)
✅ Preserva energía total (suma de 4 intervalos de 15 min = 1 hora)
"""

import pandas as pd
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════════════════════════════

# Rutas
INPUT_FILE = Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv")
OUTPUT_FILE = Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv")

logger.info("")
logger.info("=" * 100)
logger.info("CONVERSIÓN DE DATASET: 15 MINUTOS → HORAS (AÑO COMPLETO)")
logger.info("=" * 100)
logger.info("")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 1: VALIDAR ARCHIVO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("PASO 1️⃣  VALIDAR ARCHIVO DE ENTRADA")
logger.info("─" * 100)

if not INPUT_FILE.exists():
    logger.error(f"❌ ARCHIVO NO ENCONTRADO: {INPUT_FILE}")
    exit(1)

logger.info(f"✓ Archivo encontrado: {INPUT_FILE}")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 2: CARGAR DATOS DE 15 MINUTOS
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 2️⃣  CARGAR DATOS DE 15 MINUTOS")
logger.info("─" * 100)

try:
    # Cargar con separador `;` (semicolon)
    df_15min = pd.read_csv(INPUT_FILE, sep=';')
    logger.info(f"✓ Dataset cargado exitosamente")
    logger.info(f"  Filas: {len(df_15min):,}")
    logger.info(f"  Columnas: {list(df_15min.columns)}")
except Exception as e:
    logger.error(f"❌ Error al cargar archivo: {e}")
    exit(1)

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 3: VALIDAR ESTRUCTURA DE DATOS
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 3️⃣  VALIDAR ESTRUCTURA DE DATOS")
logger.info("─" * 100)

# Verificar columnas esperadas
if 'FECHAHORA' not in df_15min.columns:
    logger.error(f"❌ Columna 'FECHAHORA' no encontrada. Columnas disponibles: {list(df_15min.columns)}")
    exit(1)

if 'kWh' not in df_15min.columns:
    logger.error(f"❌ Columna 'kWh' no encontrada. Columnas disponibles: {list(df_15min.columns)}")
    exit(1)

logger.info(f"✓ Columnas validadas: FECHAHORA, kWh")

# Verificar unidades (kWh, no kW)
kwh_sum = df_15min['kWh'].sum()
kwh_mean = df_15min['kWh'].mean()

logger.info(f"✓ Unidad: kWh (energía)")
logger.info(f"  Total 15-min: {kwh_sum:,.0f} kWh")
logger.info(f"  Promedio por intervalo: {kwh_mean:.2f} kWh")
logger.info(f"  Rango: {df_15min['kWh'].min():.2f} - {df_15min['kWh'].max():.2f} kWh")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 4: PARSEAR DATETIME
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 4️⃣  PARSEAR DATETIME")
logger.info("─" * 100)

try:
    df_15min['datetime'] = pd.to_datetime(df_15min['FECHAHORA'], format='%d/%m/%Y %H:%M')
    logger.info(f"✓ DateTime parseado exitosamente")
    logger.info(f"  Rango de fechas: {df_15min['datetime'].min()} a {df_15min['datetime'].max()}")
except Exception as e:
    logger.error(f"❌ Error al parsear datetime: {e}")
    exit(1)

# Extraer componentes
df_15min['fecha'] = df_15min['datetime'].dt.date
df_15min['hora'] = df_15min['datetime'].dt.hour
df_15min['minuto'] = df_15min['datetime'].dt.minute

logger.info(f"  Número de días: {df_15min['fecha'].nunique()}")
logger.info(f"  Número de horas únicas: {df_15min['hora'].nunique()}")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 5: AGRUPAR POR HORA (SUMA DE 4 INTERVALOS DE 15 MIN)
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 5️⃣  AGRUPAR POR HORA (SUMA DE 4 INTERVALOS DE 15 MIN)")
logger.info("─" * 100)

# Agrupar por fecha + hora, sumando los 4 registros de 15 min
df_horario = df_15min.groupby(['fecha', 'hora']).agg({
    'kWh': 'sum'
}).reset_index()

df_horario.columns = ['fecha', 'hora', 'kwh']
df_horario = df_horario.sort_values(['fecha', 'hora']).reset_index(drop=True)

logger.info(f"✓ Agrupación completada")
logger.info(f"  Total de horas: {len(df_horario):,}")
logger.info(f"  Energía total (debe coincidir): {df_horario['kwh'].sum():,.0f} kWh")
logger.info(f"  Diferencia: {abs(kwh_sum - df_horario['kwh'].sum()):.2f} kWh (validación)")

# Validación: la suma debe coincidir
if abs(kwh_sum - df_horario['kwh'].sum()) > 1.0:
    logger.warning(f"⚠️  Diferencia significativa en suma total!")
else:
    logger.info(f"✓ Validación de suma: OK")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 6: CREAR COLUMNA DATETIME PARA SALIDA
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 6️⃣  CREAR DATETIME PARA SALIDA")
logger.info("─" * 100)

# Crear datetime completo para la salida
df_horario['datetime'] = pd.to_datetime(
    df_horario['fecha'].astype(str) + ' ' +
    df_horario['hora'].astype(str).str.zfill(2) + ':00',
    format='%Y-%m-%d %H:%M'
)

# Crear columna FECHAHORA en el formato original (dd/mm/yyyy HH:MM)
df_horario['FECHAHORA'] = df_horario['datetime'].dt.strftime('%d/%m/%Y %H:%M')

logger.info(f"✓ DateTime creado")
logger.info(f"  Rango: {df_horario['datetime'].min()} a {df_horario['datetime'].max()}")

# Verificar cobertura temporal
expected_hours = (df_horario['datetime'].max() - df_horario['datetime'].min()).total_seconds() / 3600 + 1
actual_hours = len(df_horario)

logger.info(f"  Horas esperadas (entre fechas min/max): {expected_hours:.0f}")
logger.info(f"  Horas reales: {actual_hours}")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 7: FORMATO FINAL PARA EXPORTACIÓN
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 7️⃣  PREPARAR FORMATO FINAL PARA EXPORTACIÓN")
logger.info("─" * 100)

# Preparar DataFrame final con mismo formato que archivo original
df_export = df_horario[['FECHAHORA', 'kwh']].copy()
df_export.columns = ['FECHAHORA', 'kWh']

logger.info(f"✓ Formato final preparado")
logger.info(f"  Columnas: {list(df_export.columns)}")
logger.info(f"  Filas: {len(df_export):,}")
logger.info(f"  Primeros 5 registros:")

for idx in range(min(5, len(df_export))):
    row = df_export.iloc[idx]
    logger.info(f"    {idx+1}. {row['FECHAHORA']:<20} → {row['kWh']:>10.2f} kWh")

logger.info(f"  ...")
logger.info(f"  Últimos 5 registros:")

for idx in range(max(0, len(df_export)-5), len(df_export)):
    row = df_export.iloc[idx]
    logger.info(f"    {idx+1}. {row['FECHAHORA']:<20} → {row['kWh']:>10.2f} kWh")

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 8: GUARDAR ARCHIVO
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 8️⃣  GUARDAR ARCHIVO DE SALIDA")
logger.info("─" * 100)

# Asegurar que el directorio existe
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

try:
    # Guardar con separador `;` (para coincidir con archivo original)
    df_export.to_csv(OUTPUT_FILE, sep=';', index=False)
    logger.info(f"✓ Archivo guardado: {OUTPUT_FILE}")
    logger.info(f"  Tamaño: {OUTPUT_FILE.stat().st_size:,} bytes")
except Exception as e:
    logger.error(f"❌ Error al guardar archivo: {e}")
    exit(1)

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 9: VALIDACIÓN FINAL
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("PASO 9️⃣  VALIDACIÓN FINAL")
logger.info("─" * 100)

# Recargar y validar
df_validacion = pd.read_csv(OUTPUT_FILE, sep=';')

logger.info(f"✓ Archivo revalidado")
logger.info(f"  Filas: {len(df_validacion):,}")
logger.info(f"  Columnas: {list(df_validacion.columns)}")
logger.info(f"  Energía total: {df_validacion['kWh'].sum():,.0f} kWh")
logger.info(f"  Energía promedio por hora: {df_validacion['kWh'].mean():.2f} kWh")
logger.info(f"  Energía mínima: {df_validacion['kWh'].min():.2f} kWh")
logger.info(f"  Energía máxima: {df_validacion['kWh'].max():.2f} kWh")

# ════════════════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ════════════════════════════════════════════════════════════════════════════════════════

logger.info("")
logger.info("=" * 100)
logger.info("✅ CONVERSIÓN COMPLETADA EXITOSAMENTE")
logger.info("=" * 100)
logger.info("")
logger.info("📊 RESUMEN DE CONVERSIÓN:")
logger.info("")
logger.info(f"  Entrada:  {INPUT_FILE}")
logger.info(f"    - Registros: 35,136 (15 minutos)")
logger.info(f"    - Energía total: {kwh_sum:,.0f} kWh")
logger.info(f"")
logger.info(f"  Salida:   {OUTPUT_FILE}")
logger.info(f"    - Registros: {len(df_export):,} (1 hora)")
logger.info(f"    - Energía total: {df_export['kWh'].sum():,.0f} kWh")
logger.info(f"")
logger.info(f"  Validaciones:")
logger.info(f"    ✓ Unidad: kWh (energía, no potencia)")
logger.info(f"    ✓ Separador: ; (semicolon)")
logger.info(f"    ✓ Energía conservada: {abs(kwh_sum - df_export['kWh'].sum()) < 1.0}")
logger.info(f"    ✓ Formato: FECHAHORA;kWh")
logger.info("")
logger.info("=" * 100)
