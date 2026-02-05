# ACTUALIZACIÓN: RUTAS FIJAS PARA DATOS REALES OE2 EN CityLearn v2

## Cambios Realizados (2026-02-05)

### ✅ Problema Identificado
El código de `dataset_builder.py` estaba buscando datos OE2 en múltiples ubicaciones con fallbacks, lo que permitía usar datos sintéticos si no encontraba los reales. Esto invalidaría el entrenamiento.

### ✅ Solución Implementada
**Archivo Actualizado:** `src/citylearnv2/dataset_builder/dataset_builder.py`

#### 1. Sección CRÍTICA Agregada (inicio de `_load_oe2_artifacts()`)
```python
# SECCIÓN CRÍTICA: CARGAR OBLIGATORIAMENTE 4 ARCHIVOS REALES DESDE data/oe2/
# Estas rutas son FIJAS y NO se pueden mover
```

Ahora se cargan OBLIGATORIAMENTE y lanza ERROR si no existen:

#### 2. Los 4 Archivos OBLIGATORIOS (con rutas FIJAS):

| Archivo | Ruta Fija | Contenido |
|---------|-----------|----------|
| **CHARGERS_REAL_HOURLY** | `data/oe2/chargers/chargers_real_hourly_2024.csv` | 8,760 horas × 129 cols (128 chargers + timestamp) |
| **CHARGERS_STATISTICS** | `data/oe2/chargers/chargers_real_statistics.csv` | Estadísticas 128 chargers × 4 columnas |
| **BESS_HOURLY** | `data/oe2/bess/bess_hourly_dataset_2024.csv` | 8,760 horas con SOC% (50-100%) |
| **MALL_DEMAND** | `data/oe2/demandamallkwh/demandamallhorakwh.csv` | 8,785 horas de demanda mall |

#### 3. Comportamiento NUEVO:

```python
if not <archivo_obligatorio>.exists():
    raise FileNotFoundError(
        "[CRITICAL ERROR] ARCHIVO OBLIGATORIO NO ENCONTRADO:\n"
        f"  Ruta fija requerida: {ruta}\n"
        "  Este archivo es OBLIGATORIO para entrenar con datos REALES.\n"
        "  NO HAY FALLBACK disponible."
    )
```

**NO se permite continuar sin estos archivos.**

#### 4. Secciones Duplicadas REMOVIDAS:
- Línea ~450: `chargers_real_candidates` (búsqueda múltiple)
- Línea ~575: `bess_hourly_candidates` (búsqueda múltiple)
- Línea ~613: `mall_demand_candidates` (búsqueda múltiple)

Ahora directamente cargadas desde rutas FIJAS al inicio.

---

## ✅ Verificación Completada

```
[PASO 1] VERIFICAR EXISTENCIA
[OK] CHARGERS_REAL_HOURLY -> data\oe2\chargers\chargers_real_hourly_2024.csv
[OK] CHARGERS_STATISTICS -> data\oe2\chargers\chargers_real_statistics.csv
[OK] BESS_HOURLY -> data\oe2\bess\bess_hourly_dataset_2024.csv
[OK] MALL_DEMAND -> data\oe2\demandamallkwh\demandamallhorakwh.csv

[PASO 2] CARGAR Y VERIFICAR CONTENIDO
[CHARGERS_REAL_HOURLY] 8760 x 129 ✓
[CHARGERS_STATISTICS] 128 x 4 ✓
[BESS_HOURLY] 8760 x 11 | SOC: 50% to 100% ✓
[MALL_DEMAND] 8785 x 1 ✓
```

---

## 🎯 Garantías Ahora Activas:

1. **OBLIGATORIO**: Los 4 archivos DEBEN existir en `data/oe2/`
2. **FIJO**: Las rutas no pueden cambiar ni moverse
3. **SIN FALLBACK**: Si falta uno, entrena... ERROR
4. **EN TRAINING**: Agentes SAC/PPO/A2C usan datos reales
5. **EN BASELINE**: Cálculos de CO₂ se hacen con datos reales

---

## 📋 Verificación Script:
```bash
python VERIFICAR_DATOS_REALES_OBLIGATORIOS.py
```

Output confirma:
- ✅ 4 archivos existen
- ✅ Dimensiones correctas
- ✅ Contenido válido
- ✅ Listo para entrenar

---

## 🚀 Próximo Paso: Entrenar con Datos REALES
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

Dataset builder cargará OBLIGATORIAMENTE desde `data/oe2/` y lanzará error si falta algo.
