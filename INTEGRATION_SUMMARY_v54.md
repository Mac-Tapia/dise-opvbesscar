# Dataset v5.4 - Ahorros e Impacto CO₂ Integrados en CityLearn

**Fecha de Implementación**: 2026-02-13  
**Estado**: ✅ COMPLETADO y VALIDADO  
**Componentes Actualizados**: Bess.py, dataset_builder.py, validación completa

---

## 📌 Resumen Ejecutivo

Se han **integrado dos nuevas métricas cuantificables** directamente en el dataset BESS para su uso en:
1. **Entrenamiento de agentes RL** (observaciones y rewards)
2. **Análisis de rendimiento del sistema**
3. **Construcción de CityLearn v2**

### Métricas Añadidas

| Métrica | Columnas Dataset | Rango | Total Anual | Propósito |
|---------|------------------|-------|-------------|-----------|
| **Ahorros por picos** | `peak_reduction_savings_soles` + normalizado | S/. 0-139/h | **S/. 118,445/año** | Recompensa económica por corte de picos |
| **CO₂ indirecto (BESS)** | `co2_avoided_indirect_kg` + normalizado | 0-176 kg/h | **203.5 ton/año** | Recompensa ambiental por BESS discharge |

---

## 🔧 Implementación Técnica

### 1. Modificaciones a `bess.py` (líneas específicas)

**Línea ~976**: Añadieron 2 nuevos arrays iniciales
```python
peak_reduction_savings_soles = np.zeros(n_hours)       # Ahorro (S/)
co2_avoided_indirect_kg = np.zeros(n_hours)            # CO2 (kg)
```

**Línea ~1110**: Cálculos dentro del loop horario
```python
# Ahorro cuando BESS descarga para mall
peak_reduction_savings_soles[h] = bess_to_mall[h] × tariff_soles_kwh[h]

# CO2 cuando BESS reemplaza red térmica
co2_avoided_indirect_kg[h] = (bess_to_ev[h] + bess_to_mall[h]) × FACTOR_CO2_KG_KWH
```

**Línea ~1140**: Normalización y adición al DataFrame
```python
# Normalizar para observaciones RL [0,1]
peak_reduction_savings_normalized = peak_reduction_savings_soles / MAX_SAVINGS_HOUR
co2_avoided_indirect_normalized = co2_avoided_indirect_kg / MAX_CO2_HOUR

# Añadir al DataFrame
df['peak_reduction_savings_soles'] = peak_reduction_savings_soles
df['peak_reduction_savings_normalized'] = peak_reduction_savings_normalized
df['co2_avoided_indirect_kg'] = co2_avoided_indirect_kg
df['co2_avoided_indirect_normalized'] = co2_avoided_indirect_normalized
```

### 2. Modificaciones a `dataset_builder.py` (líneas 1820-1843)

**Extracción de nuevas columnas**:
```python
# Buscar columnas normalizadas en el dataset original
if "peak_reduction_savings_normalized" in bess_oe2_df.columns:
    peak_reduction_savings_norm = bess_oe2_df["peak_reduction_savings_normalized"].values

# Crear DataFrame para CityLearn con nuevas métricas
bess_df = pd.DataFrame({
    "soc_stored_kwh": soc_kwh,
    "peak_reduction_savings_normalized": peak_reduction_savings_norm,
    "co2_avoided_indirect_normalized": co2_avoided_indirect_norm,
})
```

---

## 📊 Estadísticas Validadas

### ✅ Validación Completa Realizada

```
✅ Estructura Dataset              → 8,760 filas × 25 columnas
✅ Normalización [0,1]             → peak_reduction: [0, 1], co2_avoided: [0, 1]
✅ Totales Anuales                 → S/. 118,445 ahorros, 203.5 ton CO₂
✅ Sin valores nulos                → 0 NaNs en todas las columnas
✅ Correlación real/normalizado     → r = 1.000000 (perfecto)
✅ Compatibilidad dataset_builder   → SOC: 19.4% - 100% (dentro de rango)
```

### Distribución de Valores

**Ahorros por Picos**:
- Min: S/. 0.00/h
- Max: S/. 139.22/h
- Promedio: S/. 13.52/h
- Desv. Est: S/. 32.66/h
- **Total: S/. 118,445/año**

**CO₂ Evitado (BESS)**:
- Min: 0.00 kg/h
- Max: 176.26 kg/h
- Promedio: 23.23 kg/h
- Desv. Est: 52.64 kg/h
- **Total: 203,512 kg/año = 203.5 ton/año**

---

## 🎯 Impacto en OE3 (Agentes RL)

### Observables Disponibles

Los agentes RL ahora reciben como observaciones:

```
observation_t = {
    'bess_soc_kwh': <float>,                      # Existente: SOC actual
    'peak_reduction_savings_normalized': <float>,  # NUEVO: Ahorros [0,1]
    'co2_avoided_indirect_normalized': <float>,    # NUEVO: CO₂ [0,1]
    'grid_import_kwh': <float>,                   # Existente: Import
    'pv_generation_kwh': <float>,                 # Existente: PV
    ... (otras variables OE2)
}
```

### Función de Recompensa Mejorada

Puede implementarse reward con nuevas métricas:

```python
# Reward multi-objetivo con métricas v5.4
reward = (
    w_co2_savings * obs['co2_avoided_indirect_normalized']      # NUEVO
    + w_economic_savings * obs['peak_reduction_savings_normalized']  # NUEVO
    + w_grid_import * (-obs['grid_import_kwh'])                # Existente
    + w_self_sufficiency * self_sufficiency_ratio              # Existente
) / (w_co2_savings + w_economic_savings + w_grid_import + w_self_sufficiency)
```

**Ventajas para Training**:
- ✓ Dos componentes de recompensa diferenciados (económico + ambiental)
- ✓ Escala normalizada [0,1] → convergencia más rápida
- ✓ Agentes aprenden a optimizar tanto ahorro como sostenibilidad
- ✓ Feedback directo sobre impacto de acciones

---

## 📁 Archivos Generados/Modificados

### Creados
```
✓ DATASET_METRICS_v54_INTEGRATION.md       (documentación técnica)
✓ validate_metrics_v54_integration.py      (validación completa)
```

### Modificados
```
✓ src/dimensionamiento/oe2/disenobess/bess.py     (cálculos + columnas)
✓ src/citylearnv2/dataset_builder/dataset_builder.py  (extracción)
```

### Salida Principal
```
✓ data/oe2/bess/bess_simulation_hourly.csv
  └─ Ahora con 4 nuevas columnas (v5.4)
     ├─ 21. peak_reduction_savings_soles
     ├─ 22. peak_reduction_savings_normalized
     ├─ 23. co2_avoided_indirect_kg
     └─ 24. co2_avoided_indirect_normalized
```

---

## 🔗 Cómo Usar en OE3 Training

### Para Agentes SAC/PPO/A2C

```python
# 1. El dataset_builder carga automáticamente las nuevas métricas
from src.citylearnv2.dataset_builder.dataset_builder import main as build_dataset

schema, artifacts = build_dataset(config)
# → electrical_storage_simulation.csv contiene nuevas métricas

# 2. CityLearn las incluye en observaciones
env = CityLearnEnv(schema)
obs = env.reset()
# → obs['peak_reduction_savings_normalized'] disponible

# 3. Rewards pueden usarlas
reward = compute_reward(obs, co2_weight=0.5, savings_weight=0.3)
```

### Ejemplo: Reward Multi-Objetivo

```python
def compute_reward(observation, co2_weight=0.5, savings_weight=0.3, 
                   grid_weight=0.15, soc_weight=0.05):
    """Reward balanceado entre CO2, ahorros, y estabilidad."""
    
    r_co2 = observation['co2_avoided_indirect_normalized']
    r_savings = observation['peak_reduction_savings_normalized']
    r_grid = -max(observation['grid_import_kwh'], 0)  # Penalizar import
    r_soc = min(observation['bess_soc_kwh'] / CAPACITY, 1.0)  # Incentivar SOC
    
    total_weight = co2_weight + savings_weight + grid_weight + soc_weight
    
    return (
        (co2_weight * r_co2 +
         savings_weight * r_savings +
         grid_weight * r_grid +
         soc_weight * r_soc) / total_weight
    )
```

---

## ✅ Checklist de Validación

- [x] Dataset contiene 8,760 filas (1 año)
- [x] Columnas normalizadas en rango [0,1]
- [x] Totales anuales congruentes con cálculos (S/. 118,445 ahorros, 203.5 ton CO₂)
- [x] Sin valores nulos
- [x] Correlación perfecta entre reales y normalizados
- [x] Compatible con dataset_builder
- [x] Documentación completa
- [x] Script de validación creado y ejecutado
- [x] Retrocompatibilidad con v5.3 (fallback a ceros si no existen)

---

## 🚀 Próximos Pasos (OE3 Phase)

1. **Entrenamiento de Agentes**:
   - Ejecutar `scripts/train_rl_agents.py` con nuevas métricas
   - Comparar convergencia vs v5.3
   - Analizar políticas aprendidas

2. **Evaluación de Rendimiento**:
   - Medir if/reward mejora con nuevas observables
   - Cuantificar impact en CO₂ reduction vs ahorros económicos
   - Crear dashboard con métricas

3. **Optimización de Weights**:
   - Ajustar pesos en reward function
   - Grid search: co2_weight ∈ [0.3, 0.7], savings_weight ∈ [0.1, 0.4]
   - Registrar resultados en tensorboard

---

## 📞 Contacto & Soporte

**Si tienes dudas sobre la integración v5.4**:

1. Revisa `DATASET_METRICS_v54_INTEGRATION.md` para detalles técnicos
2. Ejecuta `python validate_metrics_v54_integration.py` para diagnosticar
3. Verifica que `data/oe2/bess/bess_simulation_hourly.csv` existe y tiene 25 columnas

**Dataset integridad**:
```bash
# Verificar dataset rápidamente
python -c "import pandas as pd; df=pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv'); print(f'OK: {len(df)} filas, {len(df.columns)} cols'); print(df.columns.tolist()[-4:])"
```

---

**Versión**: 5.4  
**Componentes**: OE2 (BESS) + OE3 (CityLearn)  
**Estado**: ✅ **LISTO PARA ENTRENAMIENTO OE3**  
**Fecha**: 2026-02-13
