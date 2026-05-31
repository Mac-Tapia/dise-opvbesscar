# OE3 — Reporte: Mejor agente por reducción CO₂ directo + indirecto, eficiencia del sistema y convergencia

**Fecha:** 2026-05-30
**Fuentes auditadas:** `checkpoints/SAC_CityLearn/sac_final.zip`, `checkpoints/PPO_CityLearn/ppo_final.zip`,
`checkpoints/A2C_CityLearn/a2c_final.zip`, `outputs/*_training/result_*.json`,
`outputs/*_training/trace_*.csv`, `outputs/*_training/*_convergencia_episodios.csv`,
`outputs/*_training/*_episodios_history.csv`.
**Entrenamiento:** 2026-05-28, reward v7.5, obs_dim=18, action_dim=3, 50 episodios × 8,760 timesteps = 438,000 steps/agente
**Control de procedencia:** ver `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md`. No se usaron rutas
`archive`, `archive_previous` ni `archive_v73_obs16`.

---

## 1. Resumen ejecutivo

El sistema opera con solar PV (4,162 kWp DC / 3,201 kW AC, **5,819,332 kWh/año**) + BESS (2,000 kWh / 400 kW) + 38 sockets de carga EV (270 motos + 39 mototaxis/día) en la red aislada de Iquitos (factor CO₂: **0.4521 kg CO₂/kWh**, red térmica diesel).

La evaluación multicriterio combina tres dimensiones: **(1) CO₂ indirecto evitado** (importación de red reducida), **(2) CO₂ directo evitado** (sustitución ICE→EV), y **(3) convergencia/estabilidad** del control.

### 1.1 Auditoría de fuentes vigentes

Este informe fue recalculado con los checkpoints finales y resultados guardados vigentes:

| Agente | Checkpoint final vigente | Result JSON | Trace filas | Estado |
|---|---|---|---:|---|
| SAC | `checkpoints/SAC_CityLearn/sac_final.zip` | `outputs/sac_training/result_sac.json` | 438,000 | vigente/no archive |
| PPO | `checkpoints/PPO_CityLearn/ppo_final.zip` | `outputs/ppo_training/result_ppo.json` | 438,272 | vigente/no archive |
| A2C | `checkpoints/A2C_CityLearn/a2c_final.zip` | `outputs/a2c_training/result_a2c.json` | 438,272 | vigente/no archive |

SAC sí fue comparado usando el checkpoint final actual. Con los resultados guardados actuales, SAC
mejora y converge de forma estable respecto a corridas previas, pero todavía no supera a PPO/A2C en
F2 mínimo, reward de validación ni eficiencia de importación de red.

### Veredicto

| Criterio | Mejor agente | Episodio óptimo | Valor |
|---|---|---:|---:|
| CO₂ indirecto residual mínimo (F2 canónico) | **PPO** | 49 | 3,657,483 kg CO₂/año |
| CO₂ total evitado (directo + indirecto) desde trace | **A2C** | 19 | 2,523,717 kg CO₂ evitados/año |
| CO₂ directo evitado (ICE→EV) | **PPO** | 48 | 227,155 kg CO₂ evitados/año |
| CO₂ indirecto evitado | **A2C** | 1 | 2,377,543 kg CO₂ evitados/año |
| Convergencia y estabilidad (CV plateau) | **PPO** | — | 0.034% (más estable) |
| Eficiencia importación de red (menor grid import) | **A2C** | — | 7,337,811 kWh/año (validación) |

**Agente seleccionado (criterio OE3 canónico): PPO** — menor F2 = menor CO₂ indirecto residual = mejor control ambiental operativo.
**Agente con mayor CO₂ total evitado (trace pico): A2C** — diferencia vs PPO es solo 53,763 kg/año en pico de trace (2.1%).

---

## 2. Comparativa de los tres agentes

### 2.1 Reducción de CO₂ vs línea base F0

| Agente | F2 mínimo (kg CO₂/año) | Episodio | F2 media (kg/año) | σ (kg/año) | Reducción vs F0 | CO₂ evitado vs F0 |
|---|---:|---:|---:|---:|---:|---:|
| **PPO** | **3,657,483** | **49** | 3,695,605 | 63,818 | **48.15%** | **3,396,516 kg/año** |
| A2C | 3,659,010 | 45 | 3,699,834 | 38,248 | 48.13% | 3,394,989 kg/año |
| SAC | 3,720,640 | 33 | 3,747,127 | 42,424 | 47.25% | 3,333,359 kg/año |
| F0 (referencia) | 7,053,999 | — | — | — | 0% | — |

PPO gana por **1,527 kg CO₂/año** sobre A2C y por **63,157 kg CO₂/año** sobre SAC en su episodio óptimo.

### 2.2 CO₂ directo e indirecto — mejores episodios desde trace

#### Criterio: máximo CO₂ total evitado

| Rank | Agente | Ep. trace | CO₂ evitado total | CO₂ ind. evitado | CO₂ dir. evitado | CO₂ ind. residual | Grid import (kWh) | EV carga (kWh) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | 19 | **2,523,717** | 2,299,823 | 223,894 | 3,691,968 | 7,376,095 | 272,862 |
| 2 | PPO | 48 | 2,469,954 | 2,242,799 | 227,155 | 3,660,595 | 7,366,315 | 277,180 |
| 3 | SAC | 9 | 2,456,969 | 2,249,751 | 207,218 | 3,736,781 | 7,444,515 | 250,235 |

#### Criterio: menor CO₂ indirecto residual (F2 canónico)

| Rank | Agente | Ep. trace | CO₂ ind. residual | CO₂ ind. evitado | CO₂ dir. evitado | CO₂ total evitado | Grid import (kWh) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | 49 | **3,657,484** | 2,243,142 | 222,599 | 2,465,741 | 7,360,981 |
| 2 | A2C | 45 | 3,659,010 | 2,246,403 | 221,776 | 2,468,179 | 7,328,494 |
| 3 | SAC | 33 | 3,720,640 | 2,187,247 | 217,331 | 2,404,578 | 7,447,965 |

**Observación sobre SAC mejorado:** En el mejor episodio de SAC (ep 33, F2=3,720,640), el grid import es **7,447,965 kWh** — vs 7,360,981 de PPO. La diferencia de **87,000 kWh** × 0.4521 kg CO₂/kWh = **~39,300 kg CO₂ extra/año** solo por mayor importación de red.

---

## 3. Análisis de convergencia desde trace

### 3.1 Trayectoria de reward (rolling mean 10 episodios)

```
Episodio  PPO reward   A2C reward   SAC reward
    1      -1,385.5     -1,174.5       -984.3
    5        287.8        368.6        -365.4
   10      1,291.8      1,285.2       1,217.0
   15      1,479.1      1,542.9       1,466.3
   20      1,574.1      1,574.1       1,482.2  ← SAC converge, PPO/A2C siguen mejorando
   25      1,639.7      1,610.7       1,484.0
   30      1,660.0      1,639.5       1,487.4
   35      1,664.0      1,657.7       1,479.9
   40      1,669.7      1,641.1       1,481.6
   45      1,676.1      1,647.1       1,477.4
   49      1,679.1      1,664.7       1,475.5
   50      1,676.5      1,669.2       1,475.2
```

### 3.2 CV plateau (coeficiente de variación en plateau)

| Agente | CV plateau | Interpretación |
|---|---:|---|
| **PPO** | **0.034%** | Convergencia estable óptima — variación casi nula en plateau |
| SAC | 0.065% | Converge pronto y se mantiene, pero en nivel inferior |
| A2C | 0.422% | Oscilaciones moderadas, pero reward final más alto que SAC |

### 3.3 Episodio donde cada agente alcanza plateau estable

- **PPO**: ep 25-30 (rolling CV < 1%), sigue mejorando hasta ep 49 (+2.4% adicional)
- **A2C**: ep 18-20 (rolling CV < 1%), oscila moderadamente, mejora hasta ep 50
- **SAC**: ep 18-20 (rolling CV < 0.3%), converge estable en ~1,480 reward, por debajo de PPO/A2C

---

## 4. ¿Qué pasó con SAC mejorado?

SAC fue evaluado con su checkpoint final vigente y muestra convergencia estable, pero el plateau queda en un óptimo local inferior frente a PPO/A2C. Diagnóstico detallado:

### 4.1 El síntoma
SAC alcanzó reward ~1,480 alrededor del episodio 18-20 y luego se mantuvo estable. El plateau de SAC queda **~200 puntos de reward por debajo** de PPO y A2C (1,480 vs 1,677 y 1,661 respectivamente).

### 4.2 El mecanismo — comportamiento del entropy coefficient

Desde los diagnósticos (`sac_diagnostics_history.csv`), el `ent_coef` arranca en **1.0** al inicio del episodio 1 (step ~8,762) y decrece muy lentamente:

```
Step 8,762: ent_coef = 1.000000, actor_loss = -2.054
Step 8,780: ent_coef = 0.999100, actor_loss = -2.249
Step 8,815: ent_coef = 0.997350, actor_loss = -2.572  ← actor ya muy explotador
```

El `actor_loss` se vuelve rápidamente muy negativo (~-2.5), indicando que el actor aprendió a explotar una política antes de que el mecanismo de entropía tuviera oportunidad de mantener la exploración.

### 4.3 Causas técnicas identificadas

| Causa | Evidencia | Impacto |
|---|---|---|
| `target_entropy = -3.0` con acción 3D | El estándar (-dim = -3) puede ser demasiado bajo para este problema de control mixto (BESS continuo + EV fracciones discretizadas) | SAC reduce entropía agresivamente, reduce exploración |
| `learning_starts = 5,000` con buffer 100k | Las primeras 5,000 observaciones con política aleatoria sesgan el replay buffer hacia estados de baja demanda EV | Actor aprendió a no cargar EVs en las primeras fases |
| `_patch_citylearn_sac_update()` | Parche de compatibilidad CityLearn que modifica el ciclo de actualización | Puede alterar la sincronía actor/critic |
| Arquitectura off-policy vs entorno no-estacionario | CityLearn tiene patrones estacionales fuertes; SAC off-policy reutiliza experiencias antiguas | Experiencias de episodios tempranos (peores) contaminan el buffer en episodios tardíos |

### 4.4 Consecuencia en CO₂

Porque SAC converge a una política local inferior:
- Su grid import validación es **7,456,699 kWh/año** — el mayor de los tres agentes
- Diferencia vs PPO: **+107,730 kWh/año** × 0.4521 = **+48,704 kg CO₂/año** adicionales de red
- Diferencia vs A2C: **+118,888 kWh/año** × 0.4521 = **+53,754 kg CO₂/año** adicionales de red
- Su EV charging en validación es **solo 2,400,665 kWh** CO₂ evitados vs **2,416,093** de PPO → menor sustitución ICE→EV

### 4.5 Resumen de SAC mejorado

```
SAC encontró una política aceptable (~47% reducción CO₂) y estable,
pero no encontró la mejor política guardada (~48%+ reducción). Las 30
iteraciones adicionales después del plateau no generaron mejora suficiente.

La política de SAC prioriza estabilidad del BESS pero no maximiza
la carga EV ni minimiza suficientemente la importación de red.
```

---

## 5. Control óptimo del sistema eléctrico

### 5.1 Eficiencia operativa por agente (mejor episodio canónico)

| Métrica | PPO ep49 | A2C ep45 | SAC ep33 | Ventaja |
|---|---:|---:|---:|---|
| CO₂ indirecto residual | **3,657,484** | 3,659,010 | 3,720,640 | PPO |
| Grid import (kWh) | 7,360,981 | **7,328,494** | 7,447,965 | A2C |
| CO₂ directo evitado | 222,599 | 221,776 | 217,331 | PPO |
| CO₂ indirecto evitado | 2,243,142 | **2,246,403** | 2,187,247 | A2C |
| EV carga (kWh) | 271,704 | **270,774** | 264,737 | A2C~PPO |
| Reward validación | 1,628.46 | **1,633.29** | 1,519.15 | A2C |
| CV plateau (estabilidad) | **0.034%** | 0.422% | 0.065% | PPO |
| Sigma F2 inter-episódico | 63,818 | **38,248** | 42,424 | A2C (menor varianza) |

**PPO** gana en CO₂ indirecto residual, CO₂ directo evitado y estabilidad.
**A2C** gana en importación de red (menor), CO₂ indirecto evitado y reward de validación.
**SAC** queda 3° en todas las métricas operativas de CO₂.

### 5.2 Inferencia estadística (pruebas no paramétricas — Kruskal-Wallis, Mann-Whitney, Wilcoxon)

Todas las distribuciones son **no normales** (Shapiro-Wilk rechaza H0, p < 0.001 para los tres). Las pruebas no paramétricas muestran diferencias estadísticamente significativas:

| Prueba | Resultado | p-value | Interpretación |
|---|---:|---:|---|
| Kruskal-Wallis (3 agentes) | H = 53.02 | **3.06×10⁻¹²** | Diferencias altamente significativas |
| Mann-Whitney U: PPO < SAC | U = 412 | **3.88×10⁻⁹** | PPO emite significativamente menos que SAC |
| Mann-Whitney U: PPO < A2C | U = 746 | **2.59×10⁻⁴** | PPO emite menos que A2C (confirmado) |
| Mann-Whitney U: A2C < SAC | U = 344 | **2.16×10⁻¹⁰** | A2C emite menos que SAC |
| Wilcoxon PPO < SAC | W = 23 | **5.68×10⁻¹³** | PPO superior a SAC (pareado) |
| Wilcoxon PPO < A2C | W = 385 | **7.04×10⁻³** | PPO conserva ventaja pareada sobre A2C |
| Wilcoxon A2C < SAC | W = 0 | **8.88×10⁻¹⁶** | A2C superior a SAC (máxima significancia) |

---

## 6. Ranking multicriterio final

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CRITERIO PRINCIPAL (OE3): mínimo CO₂ indirecto residual anual (F2)    │
│                                                                          │
│  #1  PPO   → 3,657,483 kg CO₂/año  (−48.15% vs F0)  ✓ SELECCIONADO   │
│  #2  A2C   → 3,659,010 kg CO₂/año  (−48.13% vs F0)                    │
│  #3  SAC   → 3,720,640 kg CO₂/año  (−47.25% vs F0)  ✗ descartado     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  CRITERIO TRACE: máximo CO₂ total evitado (directo + indirecto)         │
│                                                                          │
│  #1  A2C ep19  → 2,523,717 kg CO₂ evitados/año  ← máximo absoluto     │
│  #2  PPO ep48  → 2,469,954 kg CO₂ evitados/año  (−2.1% vs A2C pico)   │
│  #3  SAC ep9   → 2,456,969 kg CO₂ evitados/año  (−2.6% vs A2C pico)   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  CONVERGENCIA Y CONTROL ÓPTIMO                                           │
│                                                                          │
│  #1  PPO   CV = 0.034%  → convergencia más estable y consistente       │
│  #2  SAC   CV = 0.065%  → converge rápido pero en óptimo local bajo    │
│  #3  A2C   CV = 0.422%  → oscila más, pero alcanza mejor F2 promedio   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Decisión razonada

PPO es el agente que **mejor reduce el CO₂ indirecto** (emisiones residuales de red) con **48.15% de reducción vs F0** y la **convergencia más estable** (CV 0.034%). La diferencia con A2C en F2 mínimo es sólo **1,527 kg CO₂/año** (0.04%), pero la estabilidad de PPO (CV 12× mejor que A2C) hace que su política sea más confiable para operación continua.

SAC mejorado fue comparado con los checkpoints vigentes y queda **63,157 kg CO₂/año por encima de PPO** por converger a un óptimo local inferior. Su mayor importación de red (+107,730 kWh/año vs PPO) es la causa directa de la diferencia.

---

## 7. Conclusiones

1. **PPO** es el mejor agente bajo el criterio OE3 canónico: minimiza CO₂ indirecto residual (3,657,483 kg CO₂/año), mantiene la política más estable (CV plateau 0.034%), y lidera en CO₂ directo evitado (227,155 kg en ep48).

2. **A2C** es el mejor agente para **CO₂ total evitado desde trace** (2,523,717 kg en ep19) y tiene el menor grid import en validación. Es una alternativa válida para escenarios donde la métrica priorizada sea maximizar el CO₂ evitado combinado en lugar de minimizar las emisiones residuales.

3. **SAC mejorado converge de forma estable**, pero no al nivel de PPO y A2C. Su plateau a ~1,480 reward (vs ~1,670 de PPO/A2C) se explica por convergencia a una política local que resulta en mayor importación de red y menor carga EV. El parche de compatibilidad CityLearn y el target_entropy=-3.0 son factores probables de este comportamiento.

4. La diferencia PPO–A2C es estadísticamente significativa (Wilcoxon p=0.007) pero operacionalmente pequeña (1,527 kg CO₂/año = 0.04%). La elección de PPO está justificada por su mejor estabilidad de convergencia para operación real.

5. Los tres agentes reducen el CO₂ en más del **47%** respecto al escenario sin solar, sin BESS y sin RL (F0 = 7,053,999 kg CO₂/año), lo que demuestra la viabilidad del sistema de control propuesto.

---

*Generado: 2026-05-30 | Fuentes vigentes auditadas: `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md`, `reports/oe3/agents_comparison_canonical.json` y `reports/oe3/co2_trace_direct_indirect_summary.csv`*
