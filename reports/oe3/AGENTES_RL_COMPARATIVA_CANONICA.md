# OE3 - Comparativa canonica de agentes RL

**Fecha de actualizacion:** 2026-05-31
**Decision vigente:** **PPO seleccionado**
**Alcance:** SAC v8.2 reentrenado el 2026-05-30/31 con VecNormalize; PPO y A2C vigentes del 2026-05-28. Reward `CO2_DUAL_FOCUS v8.1`, `obs_dim=18`, accion 3D y 50 episodios por agente.

Nota solar: los modulos OE2 mantienen `4,050 kWp` como capacidad nominal de diseno, mientras el dataset solar vigente reporta `4,162 kWp DC` como potencia PVWatts/pdc0 y `3,201 kW AC`.

## Fuentes

- Resultados locales de entrenamiento: `outputs/sac_training/result_sac.json`,
  `outputs/ppo_training/result_ppo.json`, `outputs/a2c_training/result_a2c.json`.
- Resumen de seccion 5.2: `outputs/seccion52/resultados_seccion52.json`.
- Fuente versionada para consultas: `reports/oe3/agents_comparison_canonical.json`.
- Tabla versionada: `reports/oe3/agents_comparison_canonical.csv`.
- Lectura directa desde traces: `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md`.
- Auditoria de fuentes vigentes: `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md`.
- Informe operativo CO2/control/convergencia: `reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md`.

## Auditoria de fuentes vigentes

La comparacion usa solo checkpoints finales y resultados guardados actuales:

| Agente | Checkpoint final | Result JSON | Estado |
|---|---|---|---|
| SAC | `checkpoints/SAC_CityLearn/sac_final.zip` + `vecnormalize.pkl` | `outputs/sac_training/result_sac.json` | vigente/no archive |
| PPO | `checkpoints/PPO_CityLearn/ppo_final.zip` | `outputs/ppo_training/result_ppo.json` | vigente/no archive |
| A2C | `checkpoints/A2C_CityLearn/a2c_final.zip` | `outputs/a2c_training/result_a2c.json` | vigente/no archive |

No se usan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.

## Criterio de seleccion

El criterio principal de OE3 es minimizar `F2` anual (`kg CO2/año`) porque representa las emisiones con solar + BESS + control RL. Menor `F2` implica mejor resultado ambiental operativo.

La prueba de normalidad no se usa para elegir el agente. Se usa para decidir el tipo de inferencia: Shapiro-Wilk rechaza normalidad en las tres series, por lo que se usan pruebas no parametricas (Kruskal-Wallis, Mann-Whitney U y Wilcoxon signed-rank).

## Tabla comparativa

| Rank | Agente | F2 minimo (kg CO2/año) | Episodio optimo | F2 media (kg/año) | Sigma (kg/año) | CO2 evitado vs F0 (kg/año) | Reduccion vs F0 | CV plateau | Reward validacion | Grid import validacion (kWh) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | **3,657,484** | **49** | 3,695,605 | 63,818 | **3,396,515** | **48.15%** | **0.034%** | 1,628.46 | 7,348,968.90 |
| 2 | A2C | 3,659,010 | 45 | 3,699,834 | 38,248 | 3,394,989 | 48.13% | 0.422% | 1,633.29 | 7,337,811.00 |
| 3 | SAC | 3,693,084 | 17 | 3,711,823 | 45,486 | 3,360,915 | 47.65% | 0.036% | 1,517.13 | 7,345,853.83 |

## Por que PPO gana

PPO tiene el menor `F2` anual: **3,657,484 kg CO2/año** en el episodio 49.
A2C queda con **1,526 kg CO2/año** mas que PPO bajo el criterio canonico de minimizacion de emisiones.
SAC queda con **35,600 kg CO2/año** mas que PPO bajo el criterio canonico de minimizacion de emisiones.

SAC v8.2 mejoro despues de activar `VecNormalize` y ajustar hiperparametros, pero su mejor `F2` actual es **3,693,084 kg CO2/año** en el episodio 17; por eso no supera a PPO/A2C en la seleccion canonica.

## Lectura complementaria desde trace

El reporte `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` calcula directamente las columnas `co2_grid_kg`, `co2_avoided_indirect_kg` y `co2_avoided_direct_kg` de los traces de entrenamiento.
Con el criterio de mayor CO2 evitado total directo + indirecto, **A2C** lidera con **2,523,717 kg CO2/año evitados** en el episodio trace 19.
Para el criterio OE3 canonico de menor F2/CO2 indirecto residual, **PPO** registra **3,657,484 kg CO2/año** en el episodio trace 49.

## Inferencia estadistica

| Prueba | Resultado | Interpretacion |
|---|---:|---|
| Shapiro-Wilk SAC | W=0.385369, p=3.635e-13 | No normal |
| Shapiro-Wilk PPO | W=0.606314, p=2.420e-10 | No normal |
| Shapiro-Wilk A2C | W=0.834341, p=5.984e-06 | No normal |
| Kruskal-Wallis | H=30.593505, p=2.274e-07 | Hay diferencias entre agentes |
| Mann-Whitney U PPO < SAC | U=503, p=1.329e-07 | PPO emite menos que SAC |
| Mann-Whitney U PPO < A2C | U=746, p=2.592e-04 | PPO se compara contra A2C |
| Wilcoxon PPO < A2C | W=385, p=7.039e-03 | Comparacion pareada PPO/A2C |

## Archivos obsoletos

Los reportes binarios y figuras antiguas que declaraban SAC/A2C como seleccionados fueron retirados o reemplazados. Si aparece una salida generada bajo `outputs/*_training/`, debe tratarse como artefacto de entrenamiento, no como fuente canonica para informes.
