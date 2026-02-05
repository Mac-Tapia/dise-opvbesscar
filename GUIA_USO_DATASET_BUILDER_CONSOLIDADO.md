# 📖 GUÍA COMPLETA: Cómo Usar Dataset Builder Consolidado

**Versión**: 2.0 (2026-02-04)  
**Estado**: 🟢 Listo para Producción

---

## 🎯 OBJETIVO

Este documento explica **paso a paso** cómo usar `dataset_builder_consolidated.py` para construir datasets CityLearn v2 con integración completa de OE2 data y contexto de recompensas.

---

## 📋 TABLA DE CONTENIDOS

1. [Instalación & Setup](#instalación--setup)
2. [Uso Básico](#uso-básico)
3. [Opciones Avanzadas](#opciones-avanzadas)
4. [Troubleshooting](#troubleshooting)
5. [Ejemplos Completos](#ejemplos-completos)
6. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 💾 Instalación & Setup

### Paso 1: Verificar que el Archivo Existe
```bash
# El archivo debe estar en:
src/citylearnv2/dataset_builder/dataset_builder_consolidated.py

# Verifica:
test -f src/citylearnv2/dataset_builder/dataset_builder_consolidated.py && echo "✅ Existe" || echo "❌ No existe"
```

### Paso 2: Instalar Dependencias
```bash
# Las dependencias ya deberían estar en requirements.txt
pip install -r requirements.txt

# O si usas pip específico:
pip install pandas numpy citylearn>=2.5.0 pyyaml
```

### Paso 3: Validar la Instalación
```bash
# Ejecuta el script de validación
python validate_dataset_builder_consolidated.py

# Debe mostrar: "✅ TODAS LAS VALIDACIONES PASARON!"
```

---

## 🚀 Uso Básico

### Opción 1: Importar como Módulo (RECOMENDADO)

#### Paso 1: Importar la función
```python
from src.citylearnv2.dataset_builder.dataset_builder_consolidated import (
    build_citylearn_dataset,
    BuiltDataset,
)
from pathlib import Path
```

#### Paso 2: Llamar la función
```python
# Uso con parámetros por defecto
result = build_citylearn_dataset()

# Uso con parámetros custom
result = build_citylearn_dataset(
    processed_dir=Path("data/processed/oe3/citylearn"),
    building_name="Iquitos_EV_Mall",
    overwrite=False
)
```

#### Paso 3: Acceder a los resultados
```python
# result es de tipo BuiltDataset
print(f"Dataset directory: {result.dataset_dir}")
print(f"Schema path: {result.schema_path}")
print(f"Building name: {result.building_name}")
print(f"Timestamp: {result.timestamp}")
print(f"Specs: {result.specs}")

# Verificar que se generaron los archivos
import os
charger_csvs = result.dataset_dir / "charger_simulation_0.csv"
print(f"Charger CSV exists: {charger_csvs.exists()}")
```

### Opción 2: Usar como Script CLI

#### Paso 1: Ejecutar directamente
```bash
# Con directorio por defecto (data/processed/oe3/citylearn)
python src/citylearnv2/dataset_builder/dataset_builder_consolidated.py

# Con directorio custom
python src/citylearnv2/dataset_builder/dataset_builder_consolidated.py \
    /ruta/custom/output
```

#### Paso 2: Ver la salida
```bash
# Debe ver algo como:
# ✅ LOADING OE2 ARTIFACTS
#   ✅ Solar timeseries loaded (8760 rows)
#   ✅ Charger profiles loaded (128 chargers)
#   ✅ BESS configuration loaded
#   ✅ Mall demand loaded (optional)
# 
# ✅ INITIALIZING REWARD CONTEXT
#   ✅ IquitosContext created
#   ✅ MultiObjectiveWeights loaded
# 
# ... más outputs ...
# 
# ✅ DATASET CONSTRUCTION COMPLETE
#   Dataset: /ruta/output
#   Building: Iquitos_EV_Mall
#   Timestamp: 2026-02-04T12:34:56
```

---

## 🔧 Opciones Avanzadas

### Parámetro 1: `processed_dir`

```python
from pathlib import Path

# Opción A: Auto-detect (default)
result = build_citylearn_dataset()
# Busca automáticamente:
# 1. data/processed/oe3/citylearn/
# 2. data/oe3/citylearn/
# 3. Lanza error si no encuentra

# Opción B: Path explícito
result = build_citylearn_dataset(
    processed_dir=Path("/mi/ruta/custom/citylearn")
)

# Opción C: Usar variable de entorno
import os
output_dir = os.getenv("CITYLEARN_OUTPUT_DIR", "data/processed/oe3/citylearn")
result = build_citylearn_dataset(
    processed_dir=Path(output_dir)
)
```

### Parámetro 2: `building_name`

```python
# Opción A: Nombre por defecto
result = build_citylearn_dataset()
# Usa: "Iquitos_EV_Mall"

# Opción B: Nombre custom
result = build_citylearn_dataset(
    building_name="Mi_Edificio_Custom"
)
# Usa: "Mi_Edificio_Custom"

# Opción C: Nombre desde config
import yaml
with open("config.yaml") as f:
    config = yaml.safe_load(f)
    building = config.get("building_name", "Iquitos_EV_Mall")

result = build_citylearn_dataset(building_name=building)
```

### Parámetro 3: `overwrite`

```python
# Opción A: No sobrescribir (default, seguro)
result = build_citylearn_dataset(overwrite=False)
# Si los archivos ya existen, usa los existentes

# Opción B: Forzar regeneración
result = build_citylearn_dataset(overwrite=True)
# Elimina los archivos existentes y regenera todo
```

---

## 🔍 Entender el Workflow

### Los 7 Pasos de Construcción

```
1. INITIALIZE
   ├─ Detecta directorios
   ├─ Valida rutas
   └─ Carga configuración

2. LOAD OE2 DATA
   ├─ Solar: 8,760 hourly (obligatorio)
   ├─ Chargers: (8760, 128) shape (obligatorio)
   ├─ BESS: Optional, SOC tracking
   └─ Mall demand: Optional, hourly kW

3. LOAD REWARD CONTEXT
   ├─ IquitosContext (CO₂ factors, EV specs)
   ├─ MultiObjectiveWeights (reward priorities)
   └─ Fallback manual si rewards.py no disponible

4. VALIDATE COMPLETENESS
   ├─ Verifica presencia de todos los datos
   ├─ Valida shapes
   ├─ Chequea ranges
   └─ Fail fast si hay problemas

5. GENERATE SCHEMA
   ├─ Crea schema.json
   ├─ Embeds co2_context (para agentes)
   ├─ Embeds reward_weights (para agentes)
   └─ Escribe a disco

6. GENERATE CHARGER CSVs
   ├─ Crea 128 archivos (charger_simulation_0.csv ... 127.csv)
   ├─ Formato CityLearn v2 (8760 × 1 kW)
   ├─ Validación de shape pre-generación
   └─ Escribe a disco

7. POST-VALIDATE
   ├─ Verifica que todos los 128 CSVs existen
   ├─ Valida schema.json structure
   ├─ Chequea que rewards están presentes
   └─ Retorna BuiltDataset result
```

---

## 🧪 Validaciones Automáticas

### Validación 1: Solar Timeseries
```python
# ✅ ACEPTADO: 8,760 filas (hourly)
# ❌ RECHAZADO: 52,560 filas (15-min)
# ❌ RECHAZADO: 365 filas (daily)

# Cómo verificar manualmente:
import pandas as pd
df = pd.read_csv("data/interim/oe2/solar/pv_generation_timeseries_v2_hourly.csv")
print(f"Rows: {len(df)}")  # Debe ser 8760
print(f"Shape: {df.shape}")  # Debe ser (8760, 1)
```

### Validación 2: Charger Profiles
```python
# ✅ ACEPTADO: (8760, 128)
# ❌ RECHAZADO: (8760, 126)
# ❌ RECHAZADO: (8760,) - 1D array

# Cómo verificar manualmente:
chargers = pd.read_csv("data/interim/oe2/chargers/chargers_real_hourly_2024.csv")
print(f"Shape: {chargers.shape}")  # Debe ser (8760, 128)
```

### Validación 3: BESS Optional
```python
# ✅ ACEPTADO: (8760,) o (8760, 1)
# ⚠️  SKIPPED: Si no existe (es opcional)

# Cómo verificar manualmente:
bess = pd.read_csv("data/interim/oe2/bess/bess_hourly_dataset_2024.csv")
print(f"Shape: {bess.shape}")  # Debe ser (8760,) o (8760, 1)
```

---

## 🐛 Troubleshooting

### Problema 1: "Module not found: src.citylearnv2"
```python
# Causa: PYTHONPATH no configurado

# Solución A: Ejecutar desde root
cd /ruta/a/diseñopvbesscar  # Root del proyecto
python -c "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset"

# Solución B: Agregar a PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/ruta/a/diseñopvbesscar"
python ...

# Solución C: Usar script de wrapper
python scripts/run_oe3_build_dataset.py --config configs/default.yaml
```

### Problema 2: "Solar timeseries must be 8,760 rows"
```
Causa: Tu archivo solar tiene 52,560 filas (15-min data)

Solución: Downsample a hourly
import pandas as pd
df = pd.read_csv("path/to/15min_solar.csv")
df_hourly = df.set_index('time').resample('h').mean()
df_hourly.to_csv("solar_hourly.csv")
```

### Problema 3: "Charger profiles must be (8760, 128)"
```
Causa: Tu archivo de chargers tiene forma incorrecta

Soluciones:
1. Si tiene (8760, 126):
   - Verifica que hay 128 chargers (112 motos + 16 mototaxis)
   - Puede faltar una columna

2. Si tiene (8760,):
   - Reshape usando numpy
   import numpy as np
   arr = np.expand_dims(arr, axis=1)

3. Si tiene (365, 128):
   - Necesitas datos horarios, no diarios
   - Interpolar u obtener datos correctos
```

### Problema 4: "rewards.py not found (fallback mode)"
```
Causa: El módulo rewards.py no está disponible

Solución: Instalar o copiar rewards.py
# El dataset_builder_consolidated.py cae a "fallback mode"
# sin rewards integration, pero sigue funcionando

# Para arreglarlo:
# 1. Verifica que src/rewards/rewards.py existe
# 2. Verifica que __init__.py está en src/rewards/
# 3. Reinstala el paquete
```

### Problema 5: "Output directory already exists"
```
Causa: Los archivos de salida ya existen

Soluciones:
# Opción 1: Usar parametro overwrite
result = build_citylearn_dataset(overwrite=True)

# Opción 2: Eliminar directorio manualmente
import shutil
shutil.rmtree("data/processed/oe3/citylearn")
result = build_citylearn_dataset()

# Opción 3: Usar directorio diferente
result = build_citylearn_dataset(
    processed_dir=Path("data/processed/oe3/citylearn_v2")
)
```

---

## 📚 Ejemplos Completos

### Ejemplo 1: Uso Básico Mínimo
```python
from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset

# Construir con defaults
result = build_citylearn_dataset()

# Imprimir resultado
print(f"✅ Dataset construido en: {result.dataset_dir}")
```

### Ejemplo 2: Uso con Parámetros
```python
from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset
from pathlib import Path

# Construir con custom params
result = build_citylearn_dataset(
    processed_dir=Path("data/processed/oe3/citylearn"),
    building_name="Iquitos_EV_Mall",
    overwrite=False
)

# Acceder a resultados
print(f"Dataset dir: {result.dataset_dir}")
print(f"Schema: {result.schema_path}")
print(f"Building: {result.building_name}")

# Verificar archivos generados
import os
charger_0 = result.dataset_dir / "charger_simulation_0.csv"
schema_file = result.schema_path

assert charger_0.exists(), "Charger 0 CSV no encontrado"
assert schema_file.exists(), "Schema JSON no encontrado"
print("✅ Todos los archivos existen")
```

### Ejemplo 3: Integración con Agent Training
```python
from pathlib import Path
from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset
from src.agents.sac import make_sac

# Paso 1: Construir dataset
print("🔨 Construyendo dataset...")
dataset = build_citylearn_dataset(overwrite=False)
print(f"✅ Dataset en: {dataset.dataset_dir}")

# Paso 2: Crear ambiente CityLearn
print("🌍 Creando ambiente...")
from citylearn import CityLearnEnv
env = CityLearnEnv(dataset.schema_path)

# Paso 3: Crear y entrenar agente SAC
print("🤖 Entrenando agente...")
agent = make_sac(env)
agent.learn(total_timesteps=26280)  # 3 episodes

# Paso 4: Guardar agente
agent.save("checkpoints/sac_model")
print("✅ Agente entrenado y guardado")
```

### Ejemplo 4: Validación Manual
```python
from src.citylearnv2.dataset_builder.dataset_builder_consolidated import (
    build_citylearn_dataset,
    validate_solar_timeseries,
    validate_charger_profiles,
    validate_dataset_completeness,
)
import pandas as pd
from pathlib import Path

# Validar solar antes de construir
solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries_v2_hourly.csv")
solar_data = pd.read_csv(solar_path)
print(f"Solar shape: {solar_data.shape}")

try:
    validate_solar_timeseries(solar_data.values.ravel())
    print("✅ Solar validation passed")
except Exception as e:
    print(f"❌ Solar validation failed: {e}")

# Validar chargers antes de construir
chargers_path = Path("data/interim/oe2/chargers/chargers_real_hourly_2024.csv")
chargers_data = pd.read_csv(chargers_path)
print(f"Chargers shape: {chargers_data.shape}")

try:
    validate_charger_profiles(chargers_data.values)
    print("✅ Charger validation passed")
except Exception as e:
    print(f"❌ Charger validation failed: {e}")

# Ahora construir dataset
print("\n🔨 Construyendo dataset...")
result = build_citylearn_dataset()
print(f"✅ Dataset construido: {result.dataset_dir}")
```

---

## ❓ Preguntas Frecuentes

### P1: ¿Qué pasa si tengo 15-min solar data?
**R**: El consolidado RECHAZA automáticamente y muestra:
```
❌ DatasetValidationError: Solar timeseries must be 8,760 rows (hourly).
   Got: 52,560 rows (15-minute data)
```

**Solución**: Downsample a hourly:
```python
import pandas as pd
df = pd.read_csv("solar_15min.csv", index_col='time', parse_dates=True)
df_hourly = df.resample('h').mean()
df_hourly.to_csv("solar_hourly.csv")
```

### P2: ¿Puedo usar sin rewards.py?
**R**: SÍ. El consolidado detecta automáticamente:
```
⚠️  warnings.py not available (fallback mode)
   Rewards will be created manually
```

El dataset se genera pero sin contexto de recompensas optimizado.

### P3: ¿Cuánto tiempo toma construir el dataset?
**R**: Típicamente:
- Load data: ~1 segundo
- Validation: ~0.5 segundos
- Schema generation: ~0.1 segundos
- CSV generation (128 files): ~2-3 segundos
- **TOTAL**: ~4-5 segundos

### P4: ¿Puedo paralelizar la generación de CSVs?
**R**: El consolidado actual es secuencial, pero podrías paralelizar:
```python
from concurrent.futures import ThreadPoolExecutor
# Código custom aquí (NO incluido en consolidado)
```

### P5: ¿Dónde están los 128 CSVs generados?
**R**: En: `{processed_dir}/charger_simulation_0.csv` ... `charger_simulation_127.csv`

Ejemplo:
```bash
ls data/processed/oe3/citylearn/charger_simulation_*.csv | wc -l
# Debe mostrar: 128
```

### P6: ¿Cómo cambio los pesos de recompensa?
**R**: Los pesos están en `schema["reward_weights"]`. Puedes:

**Opción 1**: Editar después de generar
```python
import json
with open("data/processed/oe3/citylearn/schema.json") as f:
    schema = json.load(f)

schema["reward_weights"]["co2"] = 0.70  # Cambiar CO₂ weight
schema["reward_weights"]["solar"] = 0.10  # Cambiar solar weight

with open("data/processed/oe3/citylearn/schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```

**Opción 2**: Pasar config custom (si implementas en rewards.py)
```python
from src.rewards.rewards import create_iquitos_reward_weights
weights = create_iquitos_reward_weights(priority="co2_focus")
```

---

## 🎓 Aprender Más

### Documentación Relacionada
- [DATASET_BUILDER_CONSOLIDADO_v2.md](DATASET_BUILDER_CONSOLIDADO_v2.md) - Overview general
- [MAPEO_CONSOLIDACION_DETALLADO.md](MAPEO_CONSOLIDACION_DETALLADO.md) - Qué se consolidó
- [CONSOLIDACION_FINAL_RESUMEN.md](CONSOLIDACION_FINAL_RESUMEN.md) - Resumen ejecutivo

### Fuentes de Código
- Main file: `src/citylearnv2/dataset_builder/dataset_builder_consolidated.py`
- Migration tool: `migrate_dataset_builder.py`
- Validation tool: `validate_dataset_builder_consolidated.py`

### Ejecutar Ejemplos
```bash
# Validar instalación
python validate_dataset_builder_consolidated.py

# Ver plan de migración
python migrate_dataset_builder.py

# Ejecutar dataset builder
python src/citylearnv2/dataset_builder/dataset_builder_consolidated.py
```

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisar Troubleshooting arriba** (cubre 90% de casos)
2. **Ejecutar validaciones**: `python validate_dataset_builder_consolidated.py`
3. **Revisar logs**: Buscar `[ERROR]` o `[WARNING]` en la salida
4. **Contactar soporte**: Proporcionar full stack trace + logs

---

*Guía de uso: 2026-02-04*  
*Versión del consolidado: 2.0*
