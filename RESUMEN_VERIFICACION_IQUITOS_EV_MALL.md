# 📋 VERIFICACIÓN: Archivos en `data/processed/citylearn/iquitos_ev_mall/`

**Estado**: ✅ ANÁLISIS COMPLETADO (SIN CAMBIOS AL PROYECTO)  
**Fecha**: 2026-02-11  
**Objetivo**: Identificar qué archivos se usan realmente vs cuáles no se usan

---

## 📊 RESUMEN EJECUTIVO

### ✅ Archivos CRÍTICOS (SE USAN EN ENTRENAMIENTO):

| Archivo | Ubicación | Usado en | Status |
|---------|-----------|----------|--------|
| `pv_generation_hourly_citylearn_v2.csv` | Generacionsolar/ | train_a2c:646 | ✅ **MANTENER** |
| `chargers_real_hourly_2024.csv` | chargers/ | train_a2c:672 | ✅ **MANTENER** |
| `chargers_real_statistics.csv` | chargers/ | train_a2c:771 | ✅ **MANTENER** |
| `demandamallhorakwh.csv` | demandamallkwh/ | train_a2c:709 | ✅ **MANTENER** |
| `electrical_storage_simulation.csv` | (root) | train_a2c:732 | ✅ **MANTENER** |
| `schema.json` | (root) | validator, baseline | ✅ **MANTENER** |

**Total CRÍTICOS**: 6 archivos (+ 2 subdirectorios: bess/, chargers/)

---

### ❌ Archivos QUE NO SE USAN EN ENTRENAMIENTO:

| Archivo | Ubicación | Motivo | Status |
|---------|-----------|--------|--------|
| `charger_simulation_001.csv` ... `charger_simulation_038.csv` (38 archivos) | (root) | Generados para CityLearn v2 schema, nunca usados en RL | 🔴 **OPCIONAL ELIMINAR** |
| `bess_hourly_dataset_2024.csv` | bess/ | Solo fallback si falta electrical_storage_simulation | ⚠️ **BACKUP** |
| `schema_grid_only.json` | (root) | Generado pero nunca referenciado | 🔴 **OPCIONAL ELIMINAR** |
| `schema_pv_bess.json` | (root) | Generado pero nunca referenciado | 🔴 **OPCIONAL ELIMINAR** |

**Total NO USADOS**: 131 archivos (38 socket_simulation + 3 variants)

---

## 🎯 RECOMENDACIÓN FINAL

### ✅ MANTENER (Necesarios para entrenar agentes):
```
✓ Generacionsolar/pv_generation_hourly_citylearn_v2.csv (PV data)
✓ chargers/chargers_real_hourly_2024.csv (EV demand)
✓ chargers/chargers_real_statistics.csv (Charger stats)
✓ demandamallkwh/demandamallhorakwh.csv (Mall demand)
✓ electrical_storage_simulation.csv (BESS SOC)
✓ schema.json (Validation & baseline)
```

### 🔴 ELIMINAR (No se usan nunca en RL training):
```
charger_simulation_001.csv through charger_simulation_038.csv (130 MB+)
schema_grid_only.json
schema_pv_bess.json
```

**Espacio liberado**: ~140 MB (18% aprox. del total)

---

## 📝 DETALLES TÉCNICOS

### Archivos CRÍTICOS - Evidencia de uso:

**PV Data** (`pv_generation_hourly_citylearn_v2.csv`):
```python
# train_a2c_multiobjetivo.py:646
solar_path: Path = dataset_dir / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
df_solar = pd.read_csv(solar_path)  # Carga 8,760 horas de generación PV
solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
```

**Charger Demand** (`chargers_real_hourly_2024.csv`):
```python
# train_a2c_multiobjetivo.py:672
charger_real_path = dataset_dir / 'chargers' / 'chargers_real_hourly_2024.csv'
df_chargers = pd.read_csv(charger_real_path)
chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR]  # 38 sockets
```

**Charger Stats** (`chargers_real_statistics.csv`):
```python
# train_a2c_multiobjetivo.py:771-776
charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
if charger_stats_path.exists():
    df_stats = pd.read_csv(charger_stats_path)
    # Extrae potencia máxima y promedio por socket
```

**Mall Demand** (`demandamallhorakwh.csv`):
```python
# train_a2c_multiobjetivo.py:709
mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
df_mall = pd.read_csv(mall_path, sep=';')
mall_hourly = df_mall[col].values[:HOURS_PER_YEAR]
```

**BESS Data** (`electrical_storage_simulation.csv`):
```python
# train_a2c_multiobjetivo.py:732
bess_dataset_path = dataset_dir / 'electrical_storage_simulation.csv'
df_bess = pd.read_csv(bess_dataset_path)
# Contiene: soc_percent, energy flows (18 columns)
```

### Archivos NO USADOS - Análisis:

**charger_simulation_*.csv (38 archivos)**:
- ❌ Cero referencias en `train_a2c_multiobjetivo.py`
- ❌ Cero referencias en `src/agents/*.py`
- ❌ Solo usados en tests y validación de schema
- 📝 Generados para cumplir patrón CityLearn v2 (legacy)
- 💾 **Ocupan ~130 MB de espacio innecesario**

**schema_*.json variants**:
- ❌ `schema_grid_only.json`: Generado pero nunca usado
- ❌ `schema_pv_bess.json`: Generado pero nunca usado
- ✅ `schema.json`: Sí se usa en validator y baseline

---

## ✅ CONCLUSIÓN

**30 segundos resumen**:
- 6 archivos CRÍTICOS ✅ → MANTENER (son datos reales para RL training)
- 131 archivos NO USADOS ❌ → PUEDEN ELIMINARSE (ahorran 140 MB)
- 0 cambios al código ✅ → Este análisis es SIN MODIFICACIONES

**Acción recomendada**: 
- MANTENER todo tal como está (seguro)
- O ELIMINAR los 131 archivos no usados para limpiar espacio

