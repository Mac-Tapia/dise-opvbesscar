# ✅ VERIFICACIÓN SAC ↔ CityLearn v2 Conexión

## 📊 Estado de Datasets Construidos

| Dataset | Path | Columnas | Filas | Estado |
|---------|------|----------|-------|--------|
| **Solar** | `data/processed/citylearn/iquitos_ev_mall/Generacionsolar/pv_generation_hourly_citylearn_v2.csv` | 13 (timestamp, ghi, ac_power, **pv_generation_kwh**, ...) | 8760 ✓ | ✅ LISTO |
| **Chargers** | `data/processed/citylearn/iquitos_ev_mall/chargers/chargers_real_hourly_2024.csv` | 129 (timestamp + **128 sockets/actions**) | 8760 ✓ | ✅ LISTO |
| **Mall** | `data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv` | 2 (FECHAHORA, kWh) | 8760 ✓ | ✅ LISTO |
| **BESS** | `data/processed/citylearn/iquitos_ev_mall/bess/bess_hourly_dataset_2024.csv` | 12 (pv_kwh, ev_kwh, **soc_percent**, ...) | 8760 ✓ | ✅ LISTO |

---

## 🔍 Análisis de Correspondencia

### Solar Dataset Analysis
```
Columnas detectadas:
  - timestamp: datetime index
  - ghi_wm2: Irradiancia global horizontal
  - ac_power_kw: POTENCIA SOLAR AC real (columna clave)
  - pv_generation_kwh: ENERGÍA SOLAR (columna clave para recompensa)
  - dc_power_kw, dhi_wm2, etc.
```

✅ **train_sac_multiobjetivo.py expected**: `'pv_generation_kwh'` o `'ac_power_kw'`
✅ **Ambas disponibles**: El script puede usar indistintamente

**Uso en `load_datasets_from_processed()`**:
```python
col = 'pv_generation_kwh'  # ✓ Recomendado para cálculos energéticos
solar_hourly = df_solar[col].values  # 8760 valores en kWh
```

---

### Chargers Dataset Analysis
```
Columnas:
  - timestamp: datetime
  - MOTO_00_SOCKET_0 ... MOTO_19_SOCKET_1: 128 columnas de control
  
Estructura v5.2:
  - 19 cargadores = 19 motos + 4 mototaxis
  - 19 × 2 sockets = 38 sockets de control
  - PERO: Dataset tiene 128 columnas = 128 actions posibles
  
OJO: ⚠️ DISCREPANCIA
  - Script dice: n_sockets = 38 (v5.2)
  - Dataset real: 128 columnas/acciones
```

**Problema identificado**:
- `chargers_hourly.shape[1]` = 128 (no 38)
- El script valida `if n_sockets != 38` → ADVERTENCIA emitida pero NO FALLA

```python
n_sockets = chargers_hourly.shape[1]  # = 128
if n_sockets != 38:  # v5.2: 19 cargadores × 2 = 38 sockets
    print(f"⚠ ADVERTENCIA: Se encontraron {n_sockets} sockets en lugar de 38 (v5.2)")
```

**Solución**: El dataset de CityLearn usa 128 acciones (no 38). El SAC entrenará con `action_space = (128,)`.

---

### Mall Dataset Analysis
```
Columnas:
  - FECHAHORA: timestamp con ; separador
  - kWh: demanda en kWh
  
Lectura en script:
  df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
  col = df_mall.columns[-1]  # = 'kWh'
```

✅ **Compatible**: El script extrae correctamente la última columna (kWh)

---

### BESS Dataset Analysis
```
Columnas clave para observaciones:
  - datetime: timestamp
  - soc_percent: State of Charge (0-100%) → Observación clave para SAC
  - pv_kwh, ev_kwh, mall_kwh: energía por dispositivo
  - pv_to_ev_kwh, grid_to_ev_kwh, etc.: tracking de flujos
```

✅ **Compatible**: Columna `soc_percent` extraída correctamente

---

## 🏗️ Estructura CityLearn v2 Esperada

### Observation Space
```
Variables incluidas en cada obs:
1. Weather (solar): [ghi, temp, wind] → 3 dims
2. Grid data (carbon, pricing) → 2 dims
3. Building load (mall demand) → 1 dim
4. BESS SOC → 1 dim
5. Charger status (38 sockets × 3 features cada uno) → 114 dims
6. Time features (hour, month, day) → 3 dims

Total esperado: ~124 dimensiones (CityLearn v2 + Iquitos v5.2)

⚠️ ACTUAL en train_sac_multiobjetivo.py: (394,)
```

**Discrepancia**: Observation space hardcoded como (394,) en MockEnv
- Debería ser dinámico basado en dataset_builder.py
- Charger simulations_038.csv son 38 edificios separados (NO 128 actions)

---

### Action Space
```
Acciones: Control de carga en 128 puntos (chargers_real_hourly_2024.csv)
  - Rango: [0.0, 1.0] normalizado (potencia relativa)
  - Dimensión: (128,) ← Corresponde a 128 columnas de dataset

En stable-baselines3 SAC:
  action_space = spaces.Box(low=0, high=1, shape=(128,), dtype=np.float32)
```

✅ **Compatible**: Script define `shape=(129,)` pero debería ser `(128,)`

---

## ⚠️ PROBLEMAS IDENTIFICADOS EN train_sac_multiobjetivo.py

| # | Problema | Línea | Severidad | Fix |
|---|----------|-------|-----------|-----|
| 1 | MockEnv observation_space hardcoded (394,) | 357 | 🔴 CRÍTICO | Usar tamaño real del dataset |
| 2 | MockEnv action_space = (129,) pero dataset = 128 | 358 | 🟡 IMPORTANTE | Cambiar a (128,) |
| 3 | No carga realmente datos del dataset | 350-395 | 🔴 CRÍTICO | Conectar ambiente real |
| 4 | `load_datasets_from_processed()` valida pero no usa los datos | 302-334 | 🟡 IMPORTANTE | Pasar datos a environment |
| 5 | No se integra con CityLearn Environment | - | 🔴 CRÍTICO | Instantiar `CityLearnEnv` real |
| 6 | Reward function multiobjetivo no se aplica | - | 🟡 IMPORTANTE | Usar `MultiObjectiveReward` de rewards.py |

---

## 🔧 Actualizaciones Necesarias en train_sac_multiobjetivo.py

### 1. Importar CityLearn Environment
```python
from citylearn import CityLearnEnv
```

### 2. Definir paths correctos
```python
SCHEMA_PATH = Path('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json')
```

### 3. Instantiar environment real
```python
env = CityLearnEnv(schema=str(SCHEMA_PATH))
obs_dim = env.observation_space.shape[0] if hasattr(env.observation_space, 'shape') else 394
act_dim = env.action_space[0].shape[0] if isinstance(env.action_space, list) else env.action_space.shape[0]
```

### 4. Integrar reward multiobjetivo
```python
from src.rewards.rewards import MultiObjectiveReward, IquitosContext
reward_fn = MultiObjectiveReward(IquitosContext())
```

---

## ✅ Validación de Datos vs Script

### Validaciones Exitosas
- ✅ Solar timeseries: 8760 filas horarias (obligatorio)
- ✅ Chargers: Dataset real con 128 acciones
- ✅ Mall demand: 8760 filas sincronizadas
- ✅ BESS SOC: Columna `soc_percent` disponible
- ✅ Encoding UTF-8 en archivo original

### Validaciones Fallidas
- ❌ Chartgers: Se espera 38, se encuentran 128
- ❌ Observation space: Se espera (394,) pero podría variar
- ❌ Action space: Se espera (129,) pero debería ser (128,)

---

## 🎯 Recomendación Final

**Estado SAC**: ⚠️ **PARCIALMENTE LISTO**

- ✅ Datos construidos correctamente en CityLearn v2 schema
- ✅ Configuración SAC (buffer, network) está correcta (OPCIÓN A)
- ❌ Environment NO está conectado con el dataset
- ❌ MockEnv es un placeholder - necesita reemplazarse con CityLearnEnv real

**Próximos pasos**:
1. **URGENTE**: Conectar `CityLearnEnv` real en lugar de MockEnv
2. Validar observ space y action space dinámicamente
3. Integrar `MultiObjectiveReward` con pesos desde `configs/sac_optimized.json`
4. Crear wrapper para normalización de observaciones
5. Ejecutar training con datos reales

---

## 📊 Tabla de Compatibilidad Actual vs Esperada

| Componente | Expected | Actual | ✓/✗ | Notas |
|-----------|----------|--------|-----|-------|
| Solar rows | 8760 hourly | 8760 ✓ | ✓ | OK |
| Solar column | pv_generation_kwh | Available | ✓ | OK |
| Chargers rows | 8760 | 8760 ✓ | ✓ | OK |
| Chargers actions | 38 (v5.2) | 128 (real) | ⚠️ | Usar 128 |
| Mall rows | 8760 | 8760 ✓ | ✓ | OK |
| BESS rows | 8760 | 8760 ✓ | ✓ | OK |
| BESS SOC column | soc_percent | Available | ✓ | OK |
| MockEnv obs_space | (394,) | (394,) | ⚠️ | Verificar dimensión real |
| MockEnv act_space | (128,) | (129,) | ✗ | CORREGIR a 128 |
| GPU Config | Buffer 2M, Network 512x512 | ✓ | ✓ | OPCIÓN A OK |
| Device detection | Auto (CUDA/CPU) | ✓ | ✓ | OK |

---

**Fecha**: 2026-02-12  
**Generado por**: SAC Validation Script  
**Status**: 🟡 REQUIRES CRITICAL FIX (Environment Connection)
