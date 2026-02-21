# Balance.py v5.8: 4 Datasets con Auto-Actualización (2026-02-21)

## 🎯 Visión General

**balance.py SIEMPRE debe cargar 4 datasets REQUERIDOS y detectar automáticamente cambios:**

```
BALANCE.py v5.8 (AÑO 2024)
├─ DATASET 1: pv_generation_citylearn2024.csv       ← ENTRADA: PV Solar
├─ DATASET 2: chargers_ev_ano_2024_v3.csv           ← ENTRADA: EV Demand (38 sockets)  
├─ DATASET 3: demandamallhorakwh.csv                ← ENTRADA: MALL Demand
└─ DATASET 4: bess_ano_2024.csv                     ← ENTRADA: BESS Simulado (salida de bess.py)
              (generado por bess.py anteriormente)
```

## 📊 Flujo Obligatorio de Datos

```
FASE 1: BESS.PY genera simulación
        ├─ Lee 3 datasets (PV, EV, MALL)
        ├─ Ejecuta 6 fases de control BESS
        └─ Genera output: bess_ano_2024.csv ✓

FASE 2: BALANCE.PY visualiza resultados
        ├─ Lee 4 datasets (PV, EV, MALL, BESS)
        ├─ AUTO-DETECCIÓN: ¿Cambios en alguno?
        ├─ Si hay cambios → regenera gráficas
        └─ Genera output: 16 gráficas PNG ✓
```

## 🔄 Sistema de Auto-Actualización

### ¿Cómo funciona?

```python
# En balance.py línea ~1760
from src.config.datasets_config import (
    PV_GENERATION_DATA_PATH,        # Final[Path] = ...pv_generation_citylearn2024.csv
    EV_DEMAND_DATA_PATH,            # Final[Path] = ...chargers_ev_ano_2024_v3.csv
    MALL_DEMAND_DATA_PATH,          # Final[Path] = ...demandamallhorakwh.csv
    detect_dataset_changes,          # Función de auto-detección
)

# Detectar cambios basado en hash MD5
changes = detect_dataset_changes()

if changes["any_changed"]:
    print("⚠️ CAMBIOS DETECTADOS - Regenerando gráficas...")
else:
    print("✅ Datasets sin cambios - Usando datos previos")
```

### Qué se detecta:

| Dataset | Cambio Detectado | Acción |
|---------|-----------------|--------|
| PV | `changes["pv_changed"]` | Regenera gráficas de generación solar |
| EV | `changes["ev_changed"]` | Regenera gráficas de recarga EV |
| MALL | `changes["mall_changed"]` | Regenera gráficas de demanda MALL |
| BESS | Automático (depende de PV, EV, MALL) | Requiere re-ejecutar bess.py |

### Archivo de Metadata

```
data/.datasets_metadata.json (OCULTO)
{
  "pv_generation_citylearn2024.csv": {
    "file_name": "pv_generation_citylearn2024.csv",
    "file_size_bytes": 345678,
    "hash_md5": "a1b2c3d4e5f6...",
    "modified_timestamp": 1708531200.5,
    "modified_date": "2026-02-21 10:20:00"
  },
  "chargers_ev_ano_2024_v3.csv": { ... },
  "demandamallhorakwh.csv": { ... },
  "bess_ano_2024.csv": { ... }
}
```

## 📂 Rutas FIJAS de Datasets

**TODAS LAS RUTAS SON INMUTABLES** con `Final[Path]` (definidas en `datasets_config.py`):

```python
# src/config/datasets_config.py (Visión de verdad única)

PV_GENERATION_DATA_PATH: Final[Path] = (
    INTERIM_DATA_DIR / "Generacionsolar" / "pv_generation_citylearn2024.csv"
)

EV_DEMAND_DATA_PATH: Final[Path] = (
    DATA_DIR / "oe2" / "chargers" / "chargers_ev_ano_2024_v3.csv"
)

MALL_DEMAND_DATA_PATH: Final[Path] = (
    DATA_DIR / "oe2" / "demandamallkwh" / "demandamallhorakwh.csv"
)

# BESS ruta (calculada en balance.py)
BESS_DATASET_PATH = project_root / "data" / "oe2" / "bess" / "bess_ano_2024.csv"
```

## ✅ Ejecución y Validación

### 1. Ejecutar BESS primero

```bash
python -m src.dimensionamiento.oe2.disenobess.bess
```

Output esperado:
```
[OK] bess_ano_2024.csv GENERADO (8,760 horas)
```

### 2. Ejecutar BALANCE con 4 datasets

```bash
python -c "from src.dimensionamiento.oe2.balance_energetico.balance import main; main()"
```

Output esperado:
```
================================================================================
BALANCE ENERGÉTICO - Graphics Module v5.8 (CON AUTO-ACTUALIZACIÓN)
================================================================================

[AUTO-UPDATE] Detectando cambios en datasets...
✅ Datasets sin cambios

[1/4] CARGANDO PV GENERATION: pv_generation_citylearn2024.csv
      [OK] 8,760 horas - Total: 8,292,514 kWh/año

[2/4] CARGANDO EV DEMAND: chargers_ev_ano_2024_v3.csv
      [OK] 8,760 horas - Total: 408,282 kWh/año (38 sockets)

[3/4] CARGANDO MALL DEMAND: demandamallhorakwh.csv
      [OK] 8,760 horas - Total: 12,368,653 kWh/año
      [CRÍTICO] Pico MALL: 2,763.0 kW (*EXCEDE 1900 kW)

[4/4] CARGANDO BESS SIMULADO: bess_ano_2024.csv
      [OK] 8,760 horas cargadas desde BESS simulado

================================================================================
RESUMEN: 4 DATASETS CARGADOS (AUTO-UPDATE ACTIVO):
================================================================================
  [1] PV Solar:             8,292,514 kWh/año
  [2] EV Demand:              408,282 kWh/año (38 sockets)
  [3] MALL Demand:         12,368,653 kWh/año (pico: 2,763 kW)
  [4] BESS Output:          1,484,110 kWh exportados/año

  Estado: ✅ Estable - Sin cambios

Generando gráficas en outputs\balance_energetico...
  [OK] 00_BALANCE_INTEGRADO_COMPLETO.png
  [OK] 00.1_EXPORTACION_Y_PEAK_SHAVING.png
  ... (16 gráficas generadas)
  [OK] 07_utilizacion_pv.png

[OK] Graficas guardadas en: outputs\balance_energetico
```

### 3. Cuando hay cambios en datasets

Si modificas cualquiera de los 4 archivos CSV y ejecutas balance.py nuevamente:

```
[AUTO-UPDATE] Detectando cambios en datasets...
⚠️  CAMBIOS DETECTADOS EN DATASETS:
   • PV Generation (Solar)         ← Si cambió este
   • EV Demand (Motos/Mototaxis)   ← O este
   • MALL Demand (Centro Comercial) ← O este

✅ AUTO-UPDATE: Cargando datasets actualizados...
```

Las gráficas se regenerarán automáticamente con los nuevos datos.

## 📋 Validaciones Críticas

### 1. Existencia de archivos

```
[1/4] CARGANDO PV GENERATION
      ❌ PV no encontrado: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
      
      → Instrucción: Verifica ruta exacta, extensión .csv, encoding UTF-8
```

### 2. Formato de datos

```
[2/4] CARGANDO EV DEMAND
      ❌ Columna 'ev_energia_total_kwh' no encontrada
      
      → Instrucción: Verifica que el CSV tenga esta columna exacta
```

### 3. Integridad de BESS

```
[4/4] CARGANDO BESS SIMULADO
      ❌ BESS no encontrado: data/oe2/bess/bess_ano_2024.csv
      
      → Instrucción: Ejecuta bess.py primero
         python -m src.dimensionamiento.oe2.disenobess.bess
```

### 4. Pico MALL crítico

```
[CRÍTICO] Pico MALL: 2,763.0 kW (*EXCEDE 1900 kW)

→ Validación: Sistema dimensionado para soportar picos > 1900 kW
   BESS descarga por deficit solar cuando PV < demanda_mall
```

## 🔐 Garantías del Sistema

| Garantía | Implementación |
|----------|------------------|
| **Rutas inmutables** | `Final[Path]` type hints en datasets_config.py |
| **Auto-detección de cambios** | Hash MD5 + metadata tracking |
| **Datos siempre actualizados** | Regenera gráficas si hay cambios |
| **Integridad de archivos** | Validación de existencia + checksums |
| **Trazabilidad** | Metadata guardada en data/.datasets_metadata.json |

## 🚀 Caso de Uso: Actualización de Datos

### Escenario: Modifico chargers_ev_ano_2024_v3.csv

```bash
# 1. Reemplazo el archivo (mismo nombre)
cp nuevos_datos/chargers_ev_ano_2024_v3.csv data/oe2/chargers/

# 2. Ejecuto balance.py
python -c "from src.dimensionamiento.oe2.balance_energetico.balance import main; main()"

# Resultado automático:
[AUTO-UPDATE] Detectando cambios en datasets...
⚠️  CAMBIOS DETECTADOS EN DATASETS:
   • EV Demand (Motos/Mototaxis)
   
✅ AUTO-UPDATE: Cargando dataset actualizado...
[2/4] CARGANDO EV DEMAND (ACTUALIZADO)
      [OK] 8,760 horas - Total: XXX kWh/año

(Las gráficas se regeneran automáticamente con nuevos datos)
```

## ❌ Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `FileNotFoundError: pv_generation...` | Archivo no existe | Verificar ruta exacta y extensión .csv |
| `KeyError: 'energia_kwh'` | Columna no existe en CSV | Revisar nombres exactos de columnas |
| `BESS no encontrado` | No ejecutaste bess.py | Ejecutar: `python -m src.dimensionamiento.oe2.disenobess.bess` |
| `ImportError: datasets_config` | datasets_config.py no existe | Verificar: `src/config/datasets_config.py` |

## 📝 Columnas Requeridas en Datasets

### pv_generation_citylearn2024.csv
```
- energia_kwh (o primer columna)
```

### chargers_ev_ano_2024_v3.csv
```
- ev_energia_total_kwh
```

### demandamallhorakwh.csv
```
- datetime (formato: YYYY-MM-DD HH:MM:SS)
- mall_demand_kwh
```

### bess_ano_2024.csv (generado por bess.py)
```
- pv_kwh
- ev_kwh
- mall_kwh
- grid_export_kwh
- grid_import_kwh
- soc_percent
- ... y 20+ columnas más
```

## 🎓 Resumen de Cambios (v5.7 → v5.8)

| Aspecto | v5.7 | v5.8 |
|---------|------|------|
| **Datasets cargados** | 1 (bess_ano_2024.csv) | 4 (PV, EV, MALL, BESS) |
| **Auto-actualización** | No | Sí (MD5 hash detection) |
| **Rutas fijas** | Parcialmente | Completamente (Final[Path]) |
| **Detección cambios** | Manual | Automática en startup |
| **Regeneración gráficas** | Manual | Automática si detecta cambios |
| **Garantías datos** | Básicas | Completas (metadata tracking) |

## 🔗 Referencias de Código

- **Configuración rutas:** `src/config/datasets_config.py` (lines ~1-150)
- **Auto-detección:** `src/config/datasets_config.py` (función `detect_dataset_changes()`)
- **Carga 4 datasets:** `src/dimensionamiento/oe2/balance_energetico/balance.py` (lines ~1760-1890)
- **Metadata storage:** `data/.datasets_metadata.json` (hidden file)

---

**Última actualización:** 2026-02-21  
**Versión:** 5.8  
**Estado:** ✅ OPERACIONAL (16 gráficas, 4 datasets, auto-update)
