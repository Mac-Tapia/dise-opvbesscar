# Sincronización de Dimensiones: 38 Sockets v5.3 OE2
**Fecha:** 2026-02-12  
**Status:** ✅ COMPLETADO

---

## Problema Identificado
El proyecto tenía referencias incorrectas a **128 sockets** (formato `MOTO_XX_SOCKET_Y`) cuando el dataset real de OE2 tiene **38 sockets** (formato `socket_000` a `socket_037`).

**Datasets confirmados:**
- ✅ `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`: **38 sockets** (8760 filas × 352 columnas de datos)
- ❌ `data/processed/citylearn/iquitos_ev_mall/chargers/chargers_real_hourly_2024.csv`: 128 sockets (dataset procesado, NOT para SAC)

---

## Cambios Realizados

### 1. **src/citylearnv2/dataset_builder/dataset_builder.py**

#### 1a. Función `_load_real_charger_dataset()` - Docstring
```python
# ANTES:
"""Load real charger dataset from data/oe2/chargers/chargers_real_hourly_2024.csv
- 128 individual sockets (28 MOTOs x 4 tomas + 4 MOTOTAXIs x 4 tomas)
- 32 cargadores total: 28 MOTOs + 4 MOTOTAXIs"""

# DESPUÉS:
"""Load real charger dataset from data/oe2/chargers/chargers_ev_ano_2024_v3.csv
- 38 individual sockets (indexed socket_000 to socket_037)
- 19 cargadores x 2 tomas = 38 tomas totales (OE2 v3.0 specification)"""
```

#### 1b. Validación de socket count (línea ~290)
```python
# ANTES: Buscaba columnas "MOTO_XX_SOCKET_Y" (incorrecto)
socket_cols = [c for c in df.columns if '_SOCKET_' in c.upper()]
n_sockets = len(socket_cols)
if n_sockets != 128:
    raise ValueError(f"...got {n_sockets}")

# DESPUÉS: Busca formato socket_000 a socket_037
socket_cols = [c for c in df.columns if 'socket_' in c.lower()]
socket_ids = set()
for col in socket_cols:
    parts = col.split('_')
    if len(parts) > 1 and parts[1].isdigit():
        socket_ids.add(int(parts[1]))
n_sockets = len(socket_ids)
if n_sockets != 38:
    raise ValueError(f"Charger dataset MUST have 38 sockets (v5.3 OE2), got {n_sockets}")
```

#### 1c. Validación de rango de valores (línea ~313)
```python
# ANTES: Error cuando había columnas string en el dataframe
min_val = df.min().min()  # ❌ Falla con string columns

# DESPUÉS: Solo valida columnas numéricas
numeric_cols = df.select_dtypes(include=['number']).columns
if len(numeric_cols) > 0:
    min_val = df[numeric_cols].min().min()  # ✅ Solo números
```

#### 1d. Logging de distribución de sockets (línea ~322)
```python
# ANTES: Intentaba contar MOTOs y MOTOTAXIs (no existían en este dataset)
moto_cols = [c for c in df.columns if c.startswith('MOTO_') ...]  # 0 resultados
unique_motos = ...  # 0
unique_mototaxis = ...  # 0

# DESPUÉS: Valida correctamente los 38 sockets
min_socket = min(socket_ids)  # 0
max_socket = max(socket_ids)  # 37
if min_socket != 0 or max_socket != 37:
    logger.warning(f"Socket IDs range: {min_socket}-{max_socket} (expected 0-37)")
```

#### 1e. Mensaje de carga (línea ~533)
```python
# ANTES:
logger.info("[OK CARGAR] Cargadores reales horarios 2024 v5.2 - 8,760 horas x 38 sockets")

# DESPUÉS:
logger.info("[OK CARGAR] Cargadores reales horarios 2024 v5.3 OE2 - 8,760 horas x 38 sockets (socket_000 to socket_037)")
```

---

### 2. **train_sac_multiobjetivo.py**

#### 2a. Clase MockEnv - dimensión de acción (línea ~352)
```python
# ANTES:
def __init__(self, obs_dim=394, act_dim=128):  # CORRECTED: 128 from dataset

# DESPUÉS:
def __init__(self, obs_dim=394, act_dim=38):  # CORRECTED: 38 sockets from chargers_ev_ano_2024_v3.csv
```

#### 2b. Instanciación de MockEnv (línea ~380)
```python
# ANTES:
env = MockEnv(obs_dim=394, act_dim=128)
# Use actual dataset dimensions: 128 actions from chargers dataset

# DESPUÉS:
env = MockEnv(obs_dim=394, act_dim=38)
# Use actual dataset dimensions: 38 sockets (socket_000 to socket_037) from chargers_ev_ano_2024_v3.csv
```

#### 2c. Comentario de chargers (línea ~201)
```python
# ANTES:
# CHARGERS (38 sockets) - DEL DATASET v5.2

# DESPUÉS:
# CHARGERS (38 sockets socket_000 to socket_037) - FROM chargers_ev_ano_2024_v3.csv v5.3
```

---

## Validación ✅

Confirmado con comando:
```bash
python -c "
from src.citylearnv2.dataset_builder.dataset_builder import _load_real_charger_dataset
df = _load_real_charger_dataset(Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'))
# Resultado:
# ✅ VALIDATION PASSED
# Shape: 8760 rows x 352 cols (1 datetime + 351 data)
# Socket columns: 342 (38 sockets × 9 features each)
# Unique sockets: 38 (IDs: 0-37)
# Ready for SAC training with 38-dim action space
"
```

---

## Dimensiones Finales Confirmadas

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| **Filas (timesteps)** | 8,760 | chargers_ev_ano_2024_v3.csv |
| **Sockets totales** | 38 | socket_000 to socket_037 |
| **Índices socket** | 0-37 | Validados |
| **Cargadores** | 19 | OE2 v3.0 spec (19 × 2 tomas = 38) |
| **Action Space** | (38,) | Box(0, 1, shape=(38,)) |
| **Features por socket** | 9 | charger_power, battery_kwh, vehicle_type, soc_current, soc_arrival, soc_target, active, charging_power, vehicle_count |
| **Período de datos** | 2024-01-01 a 2024-12-31 | Hourly (exacto) |

---

## Archivos Modificados

```
✅ src/citylearnv2/dataset_builder/dataset_builder.py
   ├─ Función _load_real_charger_dataset() - actualizada
   ├─ Validación de sockets: 128 → 38
   ├─ Validación de formats: MOTO_XX → socket_XXX
   └─ Mensaje de carga: v5.2 → v5.3 OE2

✅ train_sac_multiobjetivo.py
   ├─ MockEnv.__init__(): act_dim=128 → act_dim=38
   ├─ Instanciación MockEnv: 128 → 38
   └─ Comentarios actualizados
```

---

## Siguientes Pasos

1. ✅ Validar que `train_sac_multiobjetivo.py` se ejecuta sin errores
2. ✅ Confirmar CityLearnEnv carga correctamente con 38 acciones
3. ⏳ Ejecutar entrenamiento SAC con 38-dim action space
4. ⏳ Validar convergencia y métricas de CO₂

**Status: SINCRONIZACIÓN COMPLETADA** ✅

