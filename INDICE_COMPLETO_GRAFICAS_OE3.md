# 📊 Índice Completo de Gráficas OE3

## 🎯 Propósito

Este documento indexa todas las gráficas generadas por el sistema OE3 de entrenamiento RL,
organizadas por categoría y propósito.

---

## 📁 Ubicaciones de Gráficas

### 1. **Gráficas de Entrenamiento Paso a Paso** ⚙️
**Ubicación**: `analyses/oe3/training/graphics/step_by_step/`

Muestra la evolución del entrenamiento desde el checkpoint inicial hasta el final.

| Archivo | Descripción | Agentes |
|---------|-------------|---------|
| `training_steps_timeline.png` | Evolución temporal de pasos (línea) | SAC, PPO, A2C |
| `checkpoint_count_by_agent.png` | Total de checkpoints guardados (barras) | SAC, PPO, A2C |
| `checkpoint_intervals.png` | Intervalos entre checkpoints (histogramas) | SAC, PPO, A2C |
| `cumulative_training_steps.png` | Acumulación de pasos (línea acumulativa) | SAC, PPO, A2C |
| `checkpoint_summary_table.png` | Tabla resumen con estadísticas | SAC, PPO, A2C |

---

### 2. **Gráficas de Entrenamiento Finales** 📈
**Ubicación**: `analyses/oe3/training/graphics/`

Gráficas de los datos reales de simulación (8,760 horas) basadas en checkpoints.

| Archivo | Descripción | Datos |
|---------|-------------|-------|
| `training_mean_reward_3agentes.png` | Evolución de recompensa promedio durante entrenamiento | SAC, PPO, A2C |
| `training_co2_3agentes.png` | Emisiones de CO₂ en episodios de entrenamiento | SAC, PPO, A2C |
| `training_grid_3agentes.png` | Importación de red durante entrenamiento | SAC, PPO, A2C |
| `training_solar_3agentes.png` | Utilización solar durante entrenamiento | SAC, PPO, A2C |

---

### 3. **Gráficas de Energía Real** ⚡
**Ubicación**: `analyses/oe3/training/graphics/`

Datos reales de 8,760 horas de simulación (timeseries completa).

| Archivo | Descripción | Datos |
|---------|-------------|-------|
| `energy_grid_import_real.png` | Importación de red acumulada (real) | SAC, A2C, Uncontrolled |
| `energy_co2_real.png` | **CO₂ REAL** (grid_import × carbon_intensity) | SAC, A2C, Uncontrolled |
| `energy_solar_generation_real.png` | Generación solar acumulada (real) | SAC, A2C, Uncontrolled |
| `energy_ev_charging_real.png` | Carga de EV acumulada (real) | SAC, A2C, Uncontrolled |

---

### 4. **Gráficas Comparativas Finales** 🏆
**Ubicación**: `analyses/oe3/training/graphics/`

Comparación de resultados finales entre agentes y baseline.

| Archivo | Descripción | Comparación |
|---------|-------------|-------------|
| `comparison_grid_import_final.png` | Importación de red final acumulada | SAC, A2C, Uncontrolled |
| `comparison_co2_final.png` | CO₂ final acumulado | SAC, A2C, Uncontrolled |
| `comparison_ev_charging_final.png` | Carga EV final acumulada | SAC, A2C, Uncontrolled |
| `comparison_kpis_matrix.png` | Matriz de KPIs finales | SAC, A2C, Uncontrolled |

---

### 5. **Gráficas de Reducción vs Baseline** 📉
**Ubicación**: `analyses/oe3/training/graphics/`

Mejora porcentual respecto al baseline (Uncontrolled).

| Archivo | Descripción | Métrica |
|---------|-------------|---------|
| `reduction_co2_vs_baseline.png` | % reducción de CO₂ respecto a baseline | SAC, A2C |
| `reduction_grid_vs_baseline.png` | % reducción de grid import vs baseline | SAC, A2C |

---

### 6. **Gráficas Históricas** 🏛️
**Ubicación**: `analyses/oe3/training/graphics/`

Gráficas individuales de cada agente (backup/referencia).

| Archivo | Descripción | Agente |
|---------|-------------|--------|
| `SAC_training_metrics.png` | Métricas de entrenamiento SAC | SAC |
| `PPO_training_metrics.png` | Métricas de entrenamiento PPO | PPO |
| `A2C_training_metrics.png` | Métricas de entrenamiento A2C | A2C |

---

## 📊 Resumen Total

- **Gráficas Step-by-Step**: 5 (nuevas)
- **Gráficas de Entrenamiento**: 4
- **Gráficas de Energía Real**: 4
- **Gráficas Comparativas**: 4
- **Gráficas de Reducción**: 2
- **Gráficas Históricas**: 3

**Total: 22 gráficas**

---

## 🔍 Guía de Uso por Tipo de Análisis

### Para Presentaciones Ejecutivas
- `comparison_kpis_matrix.png` - Vista general de resultados
- `reduction_co2_vs_baseline.png` - Impacto principal (CO₂)
- `checkpoint_count_by_agent.png` - Esfuerzo de entrenamiento

### Para Análisis Técnico Detallado
- `energy_co2_real.png` - Datos reales de emisiones
- `energy_grid_import_real.png` - Patrón de consumo de red
- `cumulative_training_steps.png` - Evolución del entrenamiento

### Para Reportes Académicos
- `training_steps_timeline.png` - Progreso de agentes
- `comparison_co2_final.png` - Resultados comparativos finales
- `energy_solar_generation_real.png` - Aprovechamiento renovable

### Para Debugging/Validación
- `checkpoint_intervals.png` - Patrón de guardado
- `checkpoint_summary_table.png` - Estadísticas consolidadas
- `TRAINING_STEPS_DOCUMENTATION.md` - Documentación técnica

---

## 📈 Métricas Clave en Gráficas

### CO₂ (kg/año)
- Calculado como: `grid_import_kwh × carbon_intensity_kg_per_kwh`
- Fuente: datos de timeseries reales (8,760 horas)
- Representa: impacto ambiental de importación de red

### Grid Import (kWh/año)
- Importación acumulativa desde la red eléctrica
- Mayor = menos autosuficiencia
- Objetivo: minimizar

### Solar Generation (kWh/año)
- Generación solar acumulativa
- Fuente: PVGIS datos reales
- Objetivo: maximizar utilización

### EV Charging (kWh/año)
- Energía total cargada a vehículos
- Métrica de servicio
- Objetivo: mantener > baseline

---

## 🎨 Código de Colores

| Agente | Color | Hex |
|--------|-------|-----|
| SAC | Rojo | #FF6B6B |
| PPO | Teal | #4ECDC4 |
| A2C | Azul | #45B7D1 |
| Uncontrolled | Menta | #95E1D3 |

---

## 🔄 Regeneración

**Gráficas Step-by-Step:**
```bash
python scripts/generar_graficas_training_steps.py
```

**Gráficas de Entrenamiento Reales:**
```bash
python scripts/generar_graficas_reales_oe3.py
```

---

## 📝 Documentación Relacionada

- [GRAFICAS_REALES_DATOS_CHECKPOINTS.md](GRAFICAS_REALES_DATOS_CHECKPOINTS.md)
- [TRAINING_STEPS_DOCUMENTATION.md](analyses/oe3/training/graphics/step_by_step/TRAINING_STEPS_DOCUMENTATION.md)
- [INDICE_GRAFICAS.md](analyses/oe3/training/graphics/INDICE_GRAFICAS.md)

---

**Generado**: 2026-01-29  
**Versión**: v2.0 (con step-by-step)  
**Total Gráficas**: 22  
**Resolución**: 300 DPI  
**Formato**: PNG RGBA
