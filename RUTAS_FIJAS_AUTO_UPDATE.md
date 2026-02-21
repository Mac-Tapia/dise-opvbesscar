# ✅ RUTAS FIJAS CON AUTO-UPDATE AUTOMÁTICO

**Fecha**: 2026-02-21  
**Versión**: v5.4 - Final con Auto-Detección de Cambios  
**Estado**: ✅ FUNCIONANDO

---

## 📌 RESUMEN EJECUTIVO

Las rutas de los 3 datasets están **FIJAS** y **NUNCA CAMBIAN**. Sin embargo, si los archivos con los **MISMOS NOMBRES** se reemplazan o actualizan, `bess.py` **detecta automáticamente los cambios** y carga los datos nuevos.

### ¿Cómo funciona?
1. Rutas FIJAS definidas en `src/config/datasets_config.py` con tipo `Final[Path]`
2. Sistema de metadata almacena hash MD5 + tamaño de archivo en `data/.datasets_metadata.json`
3. Cada ejecución de `bess.py` compara metadata actual vs anterior
4. Si hay cambios detectados → carga nuevos datos automáticamente
5. Metadata se actualiza después de cada ejecución

---

## 🔧 CONFIGURACIÓN FIJA

### **Archivo de Configuración Central**
```
d:\diseñopvbesscar\src\config\datasets_config.py
```

**Tipo**: Inmutable (type hint `Final`)  
**Uso**: Importado por `bess.py` al inicio

### **3 Rutas DEFINIDAS PARA SIEMPRE**

```python
# PV GENERATION (SOLAR)
PV_GENERATION_DATA_PATH: Final = 
    data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
    ↳ Total: 8,292,514 kWh/año
    ↳ Columna: energia_kwh
    ↳ Filas: 8,760 (1 año horario)

# EV DEMAND (MOTOS + MOTOTAXIS - 38 SOCKETS)
EV_DEMAND_DATA_PATH: Final = 
    data/oe2/chargers/chargers_ev_ano_2024_v3.csv
    ↳ Total: 408,282 kWh/año
    ↳ Columna agregada: ev_energia_total_kwh
    ↳ Filas: 8,760 (1 año horario)
    ↳ Sockets: 30 motos + 8 mototaxis

# MALL DEMAND (CENTRO COMERCIAL)
MALL_DEMAND_DATA_PATH: Final = 
    data/oe2/demandamallkwh/demandamallhorakwh.csv
    ↳ Total: 12,368,653 kWh/año
    ↳ Columna: mall_demand_kwh
    ↳ Filas: 8,760 (1 año horario)
    ↳ Pico máximo: 2,763 kW
```

---

## 🤖 SISTEMA DE AUTO-ACTUALIZACIÓN

### **Detección de Cambios en Tiempo Real**

Cada ejecución de `bess.py` hace:

```
1. LEE las rutas FIJAS desde datasets_config.py
   ↓
2. CALCULA metadata actual (hash MD5, tamaño, fecha modificación)
   ↓
3. COMPARA con metadata guardada en data/.datasets_metadata.json
   ↓
4. SI HAY CAMBIOS:
   ├─ ⚠️  Imprime: "CAMBIOS DETECTADOS EN DATASETS:"
   ├─ Lista qué datasets cambiaron (PV, EV, o MALL)
   ├─ Carga automáticamente los datos nuevos
   └─ Actualiza metadata para próxima ejecución
   
5. SI NO HAY CAMBIOS:
   ├─ ✅ Imprime: "Datasets sin cambios"
   └─ Usa datos FIJOS previos
```

### **Salida en Consola**

Si archivos se actualizaron:
```
[AUTO-UPDATE] Detectando cambios en datasets...
⚠️  CAMBIOS DETECTADOS EN DATASETS:
   • PV Generation (Solar) - DATOS ACTUALIZADOS ✓
   • EV Demand (Motos/Mototaxis) - DATOS ACTUALIZADOS ✓
   • MALL Demand (Centro Comercial) - DATOS ACTUALIZADOS ✓

✅ AUTO-UPDATE: Cargando datasets nuevos automáticamente...
```

Si archivos NO cambiaron:
```
[AUTO-UPDATE] Detectando cambios en datasets...
✅ Datasets sin cambios - Usando datos FIJOS previos
```

---

## 💾 ARCHIVO DE METADATA

### **Ubicación**
```
d:\diseñopvbesscar\data\.datasets_metadata.json
```

⚠️ **Archivo oculto** (punto al inicio) - Sistema operativo lo mantiene oculto

### **Formato**
```json
{
  "last_checked": "2026-02-21T00:30:40.123456",
  "pv": {
    "exists": true,
    "file_name": "pv_generation_citylearn2024.csv",
    "file_size_bytes": 857088,
    "modified_timestamp": 1708941600.0,
    "modified_date": "2026-02-21T00:00:00",
    "hash_md5": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
  },
  "ev": { ... },
  "mall": { ... }
}
```

### **Actualización Automática**
- Se actualiza DESPUÉS de cada ejecución de `bess.py`
- No requiere intervención manual
- Archivo invisible para usuario (punto al inicio)

---

## 🚀 EJEMPLO DE USO

### **Primer Ejecución (Línea Base)**
```bash
python -m src.dimensionamiento.oe2.disenobess.bess
```
**Output:**
```
[AUTO-UPDATE] Detectando cambios en datasets...
⚠️  CAMBIOS DETECTADOS EN DATASETS:
   • PV Generation (Solar) - DATOS ACTUALIZADOS ✓
   • EV Demand (Motos/Mototaxis) - DATOS ACTUALIZADOS ✓
   • MALL Demand (Centro Comercial) - DATOS ACTUALIZADOS ✓

✅ AUTO-UPDATE: Cargando datasets nuevos automáticamente...
```
→ Crea metadata en `data/.datasets_metadata.json`

### **Segunda Ejecución (Archivos sin cambios)**
```bash
python -m src.dimensionamiento.oe2.disenobess.bess
```
**Output:**
```
[AUTO-UPDATE] Detectando cambios en datasets...
✅ Datasets sin cambios - Usando datos FIJOS previos
```
→ Usa metadata previos (mucho más rápido)

### **Actualizar Un Dataset**
```bash
# Reemplazar archivo pv_generation_citylearn2024.csv con datos nuevos
cp ruta/al/nuevo/pv_generation_citylearn2024.csv \
   d:\diseñopvbesscar\data\oe2\Generacionsolar\pv_generation_citylearn2024.csv

# Ejecutar bess.py normalmente
python -m src.dimensionamiento.oe2.disenobess.bess
```
**Output:**
```
[AUTO-UPDATE] Detectando cambios en datasets...
⚠️  CAMBIOS DETECTADOS EN DATASETS:
   • PV Generation (Solar) - DATOS ACTUALIZADOS ✓

✅ AUTO-UPDATE: Cargando datasets nuevos automáticamente...
```
→ Detecta cambio automáticamente, carga nuevo PV, mantiene EV y MALL previos

---

## ✅ VALIDACIÓN FUNCIONAL

### **Test 1: Rutas están FIJAs**
```bash
python src/config/datasets_config.py
```
**Resultado esperado:**
```
[1] PV GENERATION (SOLAR)
Ruta FIJA: D:\diseñopvbesscar\data\oe2\Generacionsolar\pv_generation_citylearn2024.csv
Existe: True ✅

[2] EV DEMAND (MOTOS/MOTOTAXIS)
Ruta FIJA: D:\diseñopvbesscar\data\oe2\chargers\chargers_ev_ano_2024_v3.csv
Existe: True ✅

[3] MALL DEMAND (CENTRO COMERCIAL)
Ruta FIJA: D:\diseñopvbesscar\data\oe2\demandamallkwh\demandamallhorakwh.csv
Existe: True ✅

[DETECCION] Cambios automáticos en datasets
   pv_changed: ✅ Sin cambios
   ev_changed: ✅ Sin cambios
   mall_changed: ✅ Sin cambios
   any_changed: ✅ Sin cambios
```

### **Test 2: Auto-detección funciona**
```bash
# Ejecutar dos veces seguidas
python -m src.dimensionamiento.oe2.disenobess.bess
python -m src.dimensionamiento.oe2.disenobess.bess
```
**Resultado esperado:**
- Primera ejecución: Detecta cambios (es la primera vez)
- Segunda ejecución: **"Datasets sin cambios"** (metadata coinciden)

---

## 🔐 REGLAS INMUTABLES

### **NUNCA hacer:**
```python
# ❌ NO cambiar rutas en bess.py
pv_path = Path("data/oe2/generacionsolar/otro_archivo.csv")

# ❌ NO hardcodear nuevas rutas
ev_path = Path("../otra_carpeta/ev_datos.csv")

# ❌ NO reemplazar archivos en datasets_config.py
PV_GENERATION_DATA_PATH: Final = Path("...")  # ← DON'T TOUCH
```

### **SIEMPRE hacer:**
```python
# ✅ SI necesitar cambiar datos → REEMPLAZA archivo con MISMO NOMBRE
# data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
#   ↓ (reemplazar contenido, NO el nombre)

# ✅ SI necesitar actualizar → ejecuta bess.py normalmente
python -m src.dimensionamiento.oe2.disenobess.bess
#   → Auto-detecta cambios automáticamente ✓

# ✅ SI necesitar verificar → ejecuta datasets_config.py
python src/config/datasets_config.py
#   → Muestra todas las rutas FIJAS y su estado
```

---

## 📊 ARQUITECTURA DE DETECCIÓN

```
bess.py
  ├─ Importa: from src.config.datasets_config import (
  │     PV_GENERATION_DATA_PATH,        # Ruta 1 (FIJA)
  │     EV_DEMAND_DATA_PATH,            # Ruta 2 (FIJA)
  │     MALL_DEMAND_DATA_PATH,          # Ruta 3 (FIJA)
  │     detect_dataset_changes(),       # Función auto-detección
  │   )
  │
  ├─ Ejecuta: detect_dataset_changes()
  │   ├─ Lee metadata anterior (data/.datasets_metadata.json) ← si existe
  │   ├─ Calcula metadata actual:
  │   │   ├─ hash_md5 (contenido completo del archivo)
  │   │   ├─ file_size_bytes (tamaño en bytes)
  │   │   ├─ modified_timestamp (fecha último cambio)
  │   │   └─ modified_date (formato ISO)
  │   ├─ COMPARA ambos conjuntos de metadata
  │   └─ Retorna: {"pv_changed": bool, "ev_changed": bool, ...}
  │
  └─ Si hay cambios → carga nuevos datos automáticamente
      → actualiza metadata para próxima ejecución
```

---

## 🎯 CASOS DE USO

| Caso | Acción | Resultado |
|------|--------|-----------|
| **Actualizar PV** | Reemplazar `pv_generation_citylearn2024.csv` con datos nuevos (mismo nombre) | Next `bess.py` execution detecta cambio, carga nuevo PV automáticamente |
| **Actualizar EV** | Reemplazar `chargers_ev_ano_2024_v3.csv` con datos nuevos | Next `bess.py` execution detecta cambio, carga nuevo EV automáticamente |
| **Actualizar MALL** | Reemplazar `demandamallhorakwh.csv` con datos nuevos | Next `bess.py` execution detecta cambio, carga nuevo MALL automáticamente |
| **Cambiar de año (2025)** | Crear `pv_generation_citylearn2025.csv` NUEVO nombre | ❌ **NO se detecta automáticamente** (requiere cambiar ruta en datasets_config.py) |
| **Agregar dataset nuevo** | Agregar 4to archivo CSV | ❌ **NO se detecta automáticamente** (requiere agregar ruta en datasets_config.py) |
| **Limpiar metadata** | Eliminar `data/.datasets_metadata.json` | Next ejecución recalcula todo (sin cambios reales, pero recalcula hashes) |

---

## 📝 SUMARIO DE CAMBIOS

### **v5.4 (2026-02-21) - Final**
- ✅ Rutas FIJAS en `src/config/datasets_config.py` con type hints `Final[Path]`
- ✅ Sistema de detección de cambios basado en hash MD5
- ✅ Metadata guardada automático en `data/.datasets_metadata.json`
- ✅ Integración en `bess.py` línea ~4490-4530
- ✅ Console output mostrando detección automática de cambios
- ✅ Auto-actualización sin intervención manual

### **Anteriores**
- v5.3: Rutas hardcodeadas, sin detección
- v5.2: Chargers v5.2 (19 chargers × 2 sockets = 38)
- v5.1: Balance energético inicial

---

## 🆘 TROUBLESHOOTING

### **Q: ¡Ejecuté bess.py dos veces y la segunda vez dice cambios detectados!**
**A:** El sistema detectó que el archivo cambió (tamaño, contenido o fecha modificación).  
Verifica que NO moviste o copiaste el archivo después de primera ejecución.

### **Q: Cambié el contenido del CSV pero no detecta cambios**
**A:** Si cambios son muy pequeños (comentarios, espacios), hash podría ser igual.  
Ejecuta: `python src/config/datasets_config.py` para ver metadata exacta.

### **Q: ¿Dónde está el archivo de metadata?**
**A:** Está en `data/.datasets_metadata.json` (punto al inicio = archivo oculto en Windows).  
En Explorer: **Ver > Mostrar archivos ocultos** o accede por terminal.

### **Q: Quiero forzar recalcular metadata**
**A:** Elimina `data/.datasets_metadata.json` y ejecuta `bess.py` nuevamente.  
Archivo se recreará automáticamente.

### **Q: ¿Puedo cambiar rutas?**
**A:** **NO**. Rutas están FIJAS con `Final[Path]`.  
Si necesitas cambiar: 1) Haz cambios DIRECTOS a `datasets_config.py`  
2) Entiende que esto es cambio de BASELINE (afecta todos futuros)

---

## 📌 NOTA FINAL

**"Cada vez que se ejecute estas rutas de datos deben ser ejecutadas no se deben cambiar para nada, debes fijar"**

✅ **HECHO.**

Las rutas están FIJAS en `datasets_config.py` con type hints `Final[Path]`.  
Si archivos con MISMO NOMBRE se actualizan → auto-detección y carga automática.  
No hay riesgo de cambio accidental de rutas.

---

**Implementador**: GitHub Copilot  
**Fecha**: 2026-02-21  
**Verificación**: ✅ Ejecutado `bess.py` exitosamente con auto-update
