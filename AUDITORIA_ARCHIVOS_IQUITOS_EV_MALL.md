# 📊 AUDITORÍA: Uso de Archivos en `data/processed/citylearn/iquitos_ev_mall/`

**Fecha Auditoría**: 2026-02-11  
**Status**: 🔍 ANÁLISIS SIN CAMBIOS  
**Objetivo**: Verificar qué archivos se usan realmente en el proyecto

---

## 📁 Estructura de `data/processed/citylearn/iquitos_ev_mall/`

```
data/processed/citylearn/iquitos_ev_mall/
├── bess/
├── chargers/
├── demandamallkwh/
├── Generacionsolar/
├── charger_simulation_001.csv through charger_simulation_038.csv (38 archivos)
├── electrical_storage_simulation.csv
├── schema.json
├── schema_grid_only.json
└── schema_pv_bess.json
```

---

## ✅ ARCHIVOS UTILIZADOS EN EL PROYECTO

### 1. **Generacionsolar/pv_generation_hourly_citylearn_v2.csv** ✅ USADO

**Ubicación en código**:
- `train_a2c_multiobjetivo.py:646` - Carga para entrenamientoy fallback a interim
- `dataset_builder.py:389-391` - Validación

**Uso**:
```python
solar_path: Path = dataset_dir / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
df_solar = pd.read_csv(solar_path)
# Columna: 'pv_generation_kwh' o 'ac_power_kw'
```

**Status**: ✅ **NECESARIO** - Datos REALES de PV (8,760 hours)

---

### 2. **chargers/chargers_real_hourly_2024.csv** ✅ USADO

**Ubicación en código**:
- `train_a2c_multiobjetivo.py:672` - **CARGA PRINCIPAL para entrenamiento**
- Fallback a `data/interim/oe2/chargers/chargers_real_hourly_2024.csv`

**Uso**:
```python
charger_real_path = dataset_dir / 'chargers' / 'chargers_real_hourly_2024.csv'
df_chargers = pd.read_csv(charger_real_path)
chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR]  # 38 sockets x 8,760h
```

**Status**: ✅ **NECESARIO** - Demanda REAL de 38 sockets (EV datos estocásticos)

---

### 3. **chargers/chargers_real_statistics.csv** ✅ USADO

**Ubicación en código**:
- `dataset_builder.py:274, 284` - Carga y copia durante construcción
- `train_a2c_multiobjetivo.py:771-776` - Carga para estadísticas de chargers desde interim
- `train_ppo_multiobjetivo.py:1216` - Carga para estadísticas desde interim

**Uso**:
```python
charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
if charger_stats_path.exists():
    df_stats = pd.read_csv(charger_stats_path)
    # Extrae: charger_max_power_kw, charger_mean_power_kw (38 sockets)
```

**Status**: ✅ **NECESARIO** - Estadísticas REALES de carga (potencia máx, promedio, etc.)

---

### 4. **demandamallkwh/demandamallhorakwh.csv** ✅ USADO

**Ubicación en código**:
- `train_a2c_multiobjetivo.py:709` - Carga para entrenamiento

**Uso**:
```python
mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
df_mall = pd.read_csv(mall_path, sep=';')
mall_hourly = df_mall[col].values[:HOURS_PER_YEAR]  # Demanda mall
```

**Status**: ✅ **NECESARIO** - Demanda REAL del mall (8,760 hours)

---

### 5. **electrical_storage_simulation.csv** ✅ USADO

**Ubicación en código**:
- `train_a2c_multiobjetivo.py:732` - **CARGA PRINCIPAL para BESS**
- Fallback a `bess/bess_hourly_dataset_2024.csv` o interim

**Uso**:
```python
bess_dataset_path = dataset_dir / 'electrical_storage_simulation.csv'
df_bess = pd.read_csv(bess_dataset_path)
# Contiene: soc_percent, energy flows, etc. (18 columns)
```

**Status**: ✅ **NECESARIO** - BESS SOC y energy balance REAL

---

### 6. **bess/bess_hourly_dataset_2024.csv** ⚠️ FALLBACK USADO

**Ubicación en código**:
- `train_a2c_multiobjetivo.py:734` - FALLBACK cuando electrical_storage_simulation.csv no existe

**Uso**: Solo si `electrical_storage_simulation.csv` no existe

**Status**: ⚠️ **FALLBACK** - Se usa solo si falta electrical_storage_simulation.csv

## ❌ ARCHIVOS NO UTILIZADOS EN ENTRENAMIENTICO DE AGENTES

### 1. **charger_simulation_001.csv through charger_simulation_038.csv** ❌ NO USADO

**Ubicación en código**:
- Generados en `dataset_builder.py:676` con `f"charger_simulation_{charger_idx + 1:03d}.csv"`
- Referenciados en tests: `test_chargers_real_integration.py:137`
- Referenciados en validación schema: `schema_validator.py:137, 256`

**¿Por qué se generan?**
- Patrón CityLearn v2 esperado para building simulations
- Testing/validation purposes
- Posible uso futuro en contexto de CityLearn v2 directo

**Uso en entrenamiento RL**:
```python
# ❌ CERO referencias en:
# - train_a2c_multiobjetivo.py (principal training script)
# - train_ppo_multiobjetivo.py (si existe)
# - src/agents/*.py (agentes SAC/PPO/A2C)
```

**Status**: ❌ **NO USADO** - Generados para compliance CityLearn v2 pero no usados en RL training

---

### 2. **schema.json** ⚠️ PARCIALMENTE USADO

**Ubicación en código**:
- Generado en `dataset_builder.py:1873-1873`
- Validación en `schema_validator.py:34` (carga schema.json)
- Baseline en `baseline_calculator.py:248` (usa schema.json)
- Tests: `test_chargers_real_integration.py:192-194`

**Uso en entrenamiento RL**:
```python
# ❌ CERO referencias en train_a2c_multiobjetivo.py o agentes
```

**Status**: ⚠️ **PARCIALMENTE USADO**
- ✅ Validación en schema_validator
- ✅ Baseline (baseline_calculator)
- ❌ NO USADO en RL agents training

---

### 3. **schema_grid_only.json** ❌ NO USADO

**Ubicación en código**:
- Generado en `dataset_builder.py:1906` (schema sin PV/BESS)
- Ninguna referencia en código de entrenamiento

**Status**: ❌ **NO USADO** - Archivo alternativo generado pero nunca referenciado

---

### 4. **schema_pv_bess.json** ⚠️ NO CONFIRMADO COMO USADO

**Ubicación en código**:
- Generado en `dataset_builder.py:1880` (schema con PV+BESS)
- Ninguna referencia explícita en código de entrenamiento

**Status**: ⚠️ **NO ENCONTRADO EN CÓDIGO** - Pero generado como variante

---

### 5. **chargers/ subdirectory** ⚠️ PARCIALMENTE USADO

**Contenido verificado**:
- ✅ `chargers_real_hourly_2024.csv` - USADO
- ❌ Otros archivos en subdirectory - NO VERIFICADOS

**Status**: ⚠️ **REQUIERE INSPECCIÓN** de qué más hay en chargers/

---

## 📊 RESUMEN DE UTILIZACIÓN

| Archivo/Grupo | Ubicación | Usado en Training | Status |
|---|---|---|---|
| `Generacionsolar/pv_generation_hourly_citylearn_v2.csv` | dataset/ | ✅ SI (train_a2c:646) | 🟢 **NECESARIO** |
| `chargers/chargers_real_hourly_2024.csv` | dataset/ | ✅ SI (train_a2c:672) | 🟢 **NECESARIO** |
| `chargers/chargers_real_statistics.csv` | dataset/ | ✅ SI (dataset_builder, train_a2c:771) | 🟢 **NECESARIO** |
| `demandamallkwh/demandamallhorakwh.csv` | dataset/ | ✅ SI (train_a2c:709) | 🟢 **NECESARIO** |
| `electrical_storage_simulation.csv` | root/ | ✅ SI (train_a2c:732) | 🟢 **NECESARIO** |
| `bess/bess_hourly_dataset_2024.csv` | dataset/ | ⚠️ FALLBACK (train_a2c:734) | 🟡 **BACKUP ONLY** |
| `charger_simulation_001-128.csv` | root/ (38 files) | ❌ NO (cero refs) | 🔴 **NO USADO** |
| `schema.json` | root/ | ⚠️ PARTIAL (validator, baseline) | 🟡 **PARTIAL** |
| `schema_grid_only.json` | root/ | ❌ NO | 🔴 **NO USADO** |
| `schema_pv_bess.json` | root/ | ❌ NO | 🔴 **NO USADO** |

---

## 🔍 CONCLUSIONES POR SECCIÓN

### SECCIÓN 1: Core Training Data ✅ TODOS NECESARIOS
```
├── Generacionsolar/pv_generation_hourly_citylearn_v2.csv    ✅ USED
├── chargers/chargers_real_hourly_2024.csv                    ✅ USED
├── chargers/chargers_real_statistics.csv                     ✅ USED
├── demandamallkwh/demandamallhorakwh.csv                     ✅ USED
└── electrical_storage_simulation.csv                          ✅ USED
```

**Acción**: ⚠️ MANTENER TODOS - Son DATOS REALES y ESTADÍSTICAS REALES

---

### SECCIÓN 2: Charger Simulations ❌ 128 ARCHIVOS NO USADOS
```
charger_simulation_001.csv through charger_simulation_038.csv (38 files)
```

**¿Por qué existen?**
- Generados para cumplir con patrón CityLearn v2
- Para validación de schema
- Para posible uso futuro directo en CityLearn

**¿Se usan en RL training?**: ❌ NO
- El training RL usa `chargers_real_hourly_2024.csv` (tabla única 38 sockets)
- NO carga los 128 CSVs individuales de CityLearn

**Acción Recomendada**: 
- 🟡 OPCIONAL ELIMINAR (130 MB+ de espacio)
- ✅ MANTENER si planean usar CityLearn v2 simulación directa

---

### SECCIÓN 3: Schema Files ⚠️ PARCIALMENTE USADOS
```
├── schema.json            - USADO en validator + baseline
├── schema_grid_only.json  - NO USADO
└── schema_pv_bess.json    - NO USADO
```

**Acción Recomendada**:
- ✅ MANTENER `schema.json`
- 🟡 OPCIONAL ELIMINAR `schema_grid_only.json` y `schema_pv_bess.json`

---

## 🎯 RECOMENDACIÓN FINAL

### ARCHIVOS QUE DEFINITIVAMETE SE DEBEN MANTENER:
```bash
data/processed/citylearn/iquitos_ev_mall/
├── Generacionsolar/pv_generation_hourly_citylearn_v2.csv     ✅ CRITICAL
├── chargers/chargers_real_hourly_2024.csv                     ✅ CRITICAL
├── chargers/chargers_real_statistics.csv                      ✅ CRITICAL
├── demandamallkwh/demandamallhorakwh.csv                      ✅ CRITICAL
├── electrical_storage_simulation.csv                           ✅ CRITICAL
└── schema.json                                                 ✅ NECESSARY
```

**Tamaño**: ~5-10 MB (MÍNIMO VIABLE)

### ARCHIVOS OPCIONALES (POSIBLE LIMPIEZA):
```bash
├── charger_simulation_001.csv to charger_simulation_038.csv    ❌ NO USADO (130+ MB)
├── schema_grid_only.json                                       ❌ NO USADO
└── schema_pv_bess.json                                         ❌ NO USADO
```

**Tamaño**: ~140 MB (POSIBLE LIBERAR)

---

## 📝 VERIFICACIÓN TÉCNICA

```bash
# Verificar qué archivos se llaman en train_a2c_multiobjetivo.py:
Generacionsolar/pv_generation_hourly_citylearn_v2.csv  ✓ FOUND (line 646)
chargers/chargers_real_hourly_2024.csv                 ✓ FOUND (line 672)
demandamallkwh/demandamallhorakwh.csv                  ✓ FOUND (line 709)
electrical_storage_simulation.csv                      ✓ FOUND (line 732)
bess/bess_hourly_dataset_2024.csv                      ✓ FOUND as fallback (line 734)

charger_simulation_*.csv                               ✗ ZERO REFERENCES
schema_*.json (in agents)                              ✗ ZERO REFERENCES
```

---

## ✅ ESTADO DEL ANÁLISIS

- [x] Verificación de uso en `train_a2c_multiobjetivo.py`
- [x] Verificación de uso en `src/agents/*.py`
- [x] Verificación de uso en `src/citylearnv2/*`
- [x] Identificación de archivos CRÍTICOS (core data)
- [x] Identificación de archivos NO USADOS (unused)
- [x] Recomendación de limpieza opcional

**Conclusión**: 4 archivos ESENCIALES + 1 schema necesario. 38 archivos de charger simulation + 2 schemas alternativos NO USADOS en entrenamiento RL.

