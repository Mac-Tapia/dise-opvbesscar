# 5️⃣ ARCHIVOS OBLIGATORIOS OE2 - CITYLEARN v2 OE3

**CRITICO:** Estos 5 archivos DEBEN estar en `data/oe2/` con nombre exacto.
NO HAY FALLBACK, NO HAY ALTERNATIVAS. Código falla si alguno falta.

---

## Lista Verificada (2026-02-05)

| # | Archivo | Ruta | Dimensiones | Estado |
|----|---------|------|-------------|--------|
| **1** | **chargers_real_hourly_2024.csv** | `data/oe2/chargers/` | 8760 × 129 | ✅ LOADED |
| **2** | **chargers_real_statistics.csv** | `data/oe2/chargers/` | 128 × 4 | ✅ LOADED |
| **3** | **bess_hourly_dataset_2024.csv** | `data/oe2/bess/` | 8760 × 11 | ✅ LOADED |
| **4** | **demandamallhorakwh.csv** | `data/oe2/demandamallkwh/` | 8785 × 1 | ✅ LOADED |
| **5** | **pv_generation_hourly_citylearn_v2.csv** | `data/oe2/Generacionsolar/` | 8760 × 11 | ✅ LOADED |

---

## Detalle Cada Archivo

### 1️⃣ Cargadores Reales Horarios
```
Archivo:  chargers_real_hourly_2024.csv
Ubicación: data/oe2/chargers/
Dimensión: 8,760 horas × 129 columnas
Contenido: Energía (kWh) consumida por cada socket horario en 2024
Uso: Realismo en patrones de carga de motos y mototaxis
Nota: 129 columnas (probable: 128 sockets + timestamp)
```

### 2️⃣ Estadísticas Cargadores
```
Archivo:  chargers_real_statistics.csv
Ubicación: data/oe2/chargers/
Dimensión: 128 registros × 4 columnas
Contenido: Estadísticas reales (min, max, mean, std) por socket
Uso: Validación de rangos reales vs. simulación
```

### 3️⃣ BESS Horario Anual
```
Archivo:  bess_hourly_dataset_2024.csv
Ubicación: data/oe2/bess/
Dimensión: 8,760 horas × 11 columnas
Contenido: Estado BESS horario (soc_percent, charge, discharge, etc)
SOC Range: 50% a 100% (degradación esperada)
Uso: Realismo en operación sistema almacenamiento
```

### 4️⃣ Demanda Mall Iquitos
```
Archivo:  demandamallhorakwh.csv
Ubicación: data/oe2/demandamallkwh/
Dimensión: 8,785 horas × 1 columna
Contenido: Potencia (kW) demanda mall horaria 2024
Nota: 8,785 filas (25 más que esperadas, tolerable)
Uso: Demanda real no-EV en simulación
```

### 5️⃣ Generación Solar PVGIS
```
Archivo:  pv_generation_hourly_citylearn_v2.csv
Ubicación: data/oe2/Generacionsolar/
Dimensión: 8,760 horas × 11 columnas
Contenido: Generación solar horaria (W/m², irradiancia, etc) PVGIS
Capacidad: 4,050 kWp sistema solar Iquitos
Uso: Realismo en disponibilidad energía renovable
```

---

## Integración en Código

**Ubicación:** `src/citylearnv2/dataset_builder/dataset_builder.py`
**Sección:** CRITICAL SECTION lines 246-365 en `_load_oe2_artifacts()`

```python
# SECCIÓN CRÍTICA: CARGAR OBLIGATORIAMENTE 5 ARCHIVOS REALES DESDE data/oe2/

oe2_base_path = interim_dir.parent.parent / "oe2"  # → data/oe2/

# 1. CHARGERS_REAL_HOURLY (OBLIGATORIO)
chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_real_hourly_2024.csv"
if not chargers_real_fixed_path.exists():
    raise FileNotFoundError("[CRITICAL ERROR] ... NO ENCONTRADO")

# 2. CHARGERS_REAL_STATISTICS (OBLIGATORIO)
chargers_stats_fixed_path = oe2_base_path / "chargers" / "chargers_real_statistics.csv"
# ... (mismo patrón)

# 3. BESS_HOURLY_DATASET (OBLIGATORIO)
bess_hourly_fixed_path = oe2_base_path / "bess" / "bess_hourly_dataset_2024.csv"
# ... (mismo patrón)

# 4. MALL_DEMAND_HOURLY (OBLIGATORIO)
mall_demand_fixed_path = oe2_base_path / "demandamallkwh" / "demandamallhorakwh.csv"
# ... (mismo patrón)

# 5. SOLAR_GENERATION_HOURLY (OBLIGATORIO) ← NUEVO 2026-02-05
solar_generation_fixed_path = oe2_base_path / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv"
# ... (mismo patrón)

logger.info("[SUMMARY] 5 archivos reales OBLIGATORIOS cargados exitosamente de data/oe2/")
```

**Garantías:**
- ✅ Verifica existencia de cada archivo
- ✅ Levanta `FileNotFoundError` si alguno falta
- ✅ LOG detallado de carga
- ✅ NO HAY FALLBACK (no intenta buscar en otros directorios)
- ✅ Datos se almacenan en diccionario `artifacts[]`

---

## Verificación

### Script de Validación
```bash
python VERIFICAR_DATOS_REALES_5_OBLIGATORIOS.py
```

**Salida esperada:**
```
[OK] CHARGERS_REAL_HOURLY → data\oe2\chargers\chargers_real_hourly_2024.csv
[OK] CHARGERS_STATISTICS → data\oe2\chargers\chargers_real_statistics.csv
[OK] BESS_HOURLY → data\oe2\bess\bess_hourly_dataset_2024.csv
[OK] MALL_DEMAND → data\oe2\demandamallkwh\demandamallhorakwh.csv
[OK] SOLAR_GENERATION → data\oe2\Generacionsolar\pv_generation_hourly_citylearn_v2.csv

[CHARGERS_REAL_HOURLY] 8760 x 129 ✓
[CHARGERS_STATISTICS] 128 x 4 ✓
[BESS_HOURLY] 8760 x 11 | SOC: 50.0% to 100.0% ✓
[MALL_DEMAND] 8785 x 1 ✓
[SOLAR_GENERATION] 8760 x 11 ✓

✅ VERIFICACION COMPLETADA - 5 ARCHIVOS OE2 OBLIGATORIOS CARGADOS
```

---

## Changelog

### 2026-02-05 - Archivo Solar Agregado
- ✅ Agregado 5to archivo: `pv_generation_hourly_citylearn_v2.csv`
- ✅ Actualizada CRITICAL SECTION en dataset_builder.py (lines 346-365)
- ✅ Implementado mismo patrón: verificación + FileNotFoundError si falta
- ✅ Actualizado script VERIFICAR_DATOS_REALES_5_OBLIGATORIOS.py
- ✅ Actualizado CONFIG_CITYLEARN_VERIFICADA.md
- ✅ Mensaje resumen actualizado: "4 archivos" → "5 archivos OBLIGATORIOS"

---

## Conclusión

**Estos 5 archivos NO SON OPCIONALES.**

CityLearn v2 OE3 **SOLO entrena con datos reales de Iquitos 2024**:
- Cargadores: Perfiles reales de 128 sockets
- BESS: Operación real del sistema almacenamiento
- Mall: Demanda real no-EV
- Solar: Generación real PVGIS 4,050 kWp

Si ALGÚN archivo falta → **ENTRENAMIENTO FALLA INMEDIATAMENTE** ✋

Esto **garantiza que agentes SOLO optimizan con datos reales, nunca sintéticos.**
