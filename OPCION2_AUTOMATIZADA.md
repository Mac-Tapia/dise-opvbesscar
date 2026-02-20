# OPCION 2 (AUTOMATIZADA) - Cambiar SOC mínimo del BESS

## ¿Cómo funciona ahora?

Ya **no necesitas** ejecutar transformaciones o regeneraciones manuales.

El sistema detecta automáticamente cambios en `bess.py` y regenera todo en background.

---

## PASO 1: Modificar bess.py (línea 197)

**Archivo:** `src/dimensionamiento/oe2/disenobess/bess.py`  
**Línea:** 197

### Cambio Simple:

```python
# ANTES (SOC mínimo = 20%)
BESS_SOC_MIN_V53 = 0.20

# DESPUES (SOC mínimo = 15%, por ejemplo)
BESS_SOC_MIN_V53 = 0.15
```

---

## PASO 2: El sistema regenera AUTOMÁTICAMENTE

Al ejecutar **cualquier** script que importe `bess.py`, el detector automático:

1. ✅ Detecta el cambio en `BESS_SOC_MIN_V53`
2. ✅ Regenera `data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv`
3. ✅ Regenera `reports/balance_energetico/*.png` (15 gráficos)
4. ✅ Valida que todo esté correcto

**Sin que hagas nada adicional.**

---

## Ejemplos de cómo se activa:

```bash
# Opción A: Script de análisis (lo que más usas)
python scripts/regenerate_graphics_v57.py
# → Automáticamente detecta cambios y regenera

# Opción B: Script de transformación
python scripts/transform_dataset_v57.py
# → Automáticamente detecta cambios y regenera

# Opción C: Script manual de validación
python verify_soc_min.py
# → Automáticamente detecta cambios y regenera
```

---

## ¿Qué pasa si cambio múltiples parámetros?

```python
# src/dimensionamiento/oe2/disenobess/bess.py

# Puedo cambiar cualquiera de estos:
BESS_CAPACITY_KWH_V53 = 2000.0    # Capacidad (kWh)
BESS_POWER_KW_V53 = 400.0         # Potencia (kW)
BESS_SOC_MIN_V53 = 0.20           # SOC mínimo (0.20 = 20%)
BESS_SOC_MAX_V53 = 1.00           # SOC máximo (1.00 = 100%)
BESS_DOD_V53 = 0.80               # Profundidad descarga (0.80 = 80%)

# El sistema detecta TODOS los cambios y regenera automáticamente
```

---

## ¿Cómo funciona internamente?

```
bess.py
  ↓ (al importarse)
  ↓ ejecuta: from . import bess_auto_update
  ↓
bess_auto_update.py
  ↓ (detecta cambios)
  ↓ compara hash de parámetros
  ↓ si cambió → regenera todo
```

**Archivo control:** `data/.bess_state_cache.json` (guardamos estado anterior)

---

## ✅ Verificar cambios efectuados

```bash
# Ver qué se detectó y regeneró
python verify_soc_min.py

# Ver los gráficos regenerados
ls -lh reports/balance_energetico/*.png
```

---

## 🎯 Flujo simplificado (antes vs después)

### ANTES (manual):
1. Editar bess.py línea 197
2. Ejecutar `python scripts/transform_dataset_v57.py`
3. Ejecutar `python scripts/regenerate_graphics_v57.py`
4. Ejecutar `python verify_soc_min.py`
5. Verificar archivos manualmente

### AHORA (automático):
1. Editar bess.py línea 197
2. Ejecutar cualquier script normalmente
3. ✅ Hecho! (se regeneró automáticamente)

---

## ⚠️ Si algo no se regenera automáticamente

Si editas bess.py pero no se regenera, puedes forzar manualmente:

```bash
# Opción 1 (recomendado): Script automático completo
python opcion2_completo.py

# Opción 2: Regenerar todo manualmente (como antes)
python scripts/transform_dataset_v57.py
python scripts/regenerate_graphics_v57.py
python verify_soc_min.py
```

---

## Estado actual (2026-02-19)

✅ Sistema automático activo  
✅ SOC mínimo: 20.0%  
✅ Detector integrado en bess.py  
✅ Cache de estado en: `data/.bess_state_cache.json`
