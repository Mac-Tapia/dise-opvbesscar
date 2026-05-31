# OE3 - Comparativa canonica de agentes RL

**Fecha de actualizacion:** 2026-05-30
**Decision vigente:** **PPO seleccionado**
**Alcance:** reentrenamiento SAC -> PPO -> A2C de 2026-05-28 con reward v7.5, `obs_dim=18`,
accion 3D y 50 episodios por agente.

Nota solar: los modulos OE2 mantienen `4,050 kWp` como capacidad nominal de diseno, mientras el
dataset solar vigente reporta `4,162 kWp DC` como potencia PVWatts/pdc0 y `3,201 kW AC`.

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
| SAC | `checkpoints/SAC_CityLearn/sac_final.zip` | `outputs/sac_training/result_sac.json` | vigente/no archive |
| PPO | `checkpoints/PPO_CityLearn/ppo_final.zip` | `outputs/ppo_training/result_ppo.json` | vigente/no archive |
| A2C | `checkpoints/A2C_CityLearn/a2c_final.zip` | `outputs/a2c_training/result_a2c.json` | vigente/no archive |

No se usan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.

## Criterio de seleccion

El criterio principal de OE3 es minimizar `F2` anual (`kg CO2/año`) porque representa las emisiones
con solar + BESS + control RL. Menor `F2` implica mejor resultado ambiental operativo.

La prueba de normalidad no se usa para elegir el agente. Se usa para decidir el tipo de inferencia:
Shapiro-Wilk rechaza normalidad en las tres series, por lo que se usan pruebas no parametricas
(Kruskal-Wallis, Mann-Whitney U y Wilcoxon signed-rank).

## Tabla comparativa

| Rank | Agente | F2 minimo (kg CO2/año) | Episodio optimo | F2 media (kg/año) | Sigma (kg/año) | CO2 evitado vs F0 (kg/año) | Reduccion vs F0 | CV plateau | Reward validacion | Grid import validacion (kWh) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | **3,657,483** | **49** | 3,695,605 | 63,818 | **3,396,516** | **48.15%** | **0.034%** | 1,628.46 | 7,348,968.90 |
| 2 | A2C | 3,659,010 | 45 | 3,699,834 | 38,248 | 3,394,989 | 48.13% | 0.422% | 1,633.29 | 7,337,811.00 |
| 3 | SAC | 3,720,640 | 33 | 3,747,127 | 42,424 | 3,333,359 | 47.25% | 0.065% | 1,519.15 | 7,456,698.97 |

## Por que PPO gana

PPO tiene el menor `F2` anual: **3,657,483 kg CO2/año** en el episodio 49. A2C queda segundo por una
diferencia pequena (**1,527 kg CO2/año** mas que PPO), pero el criterio de seleccion es minimizacion
de emisiones y por tanto PPO queda primero.

SAC no gana en la corrida vigente porque su mejor `F2` es **3,720,640 kg CO2/año**, equivalente a
**63,157 kg CO2/año** mas que PPO. Aunque SAC mantiene bajo `CV plateau`, su nivel de emisiones
controladas queda por encima de PPO y A2C.

## Lectura complementaria desde trace

El reporte `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` calcula directamente las columnas
`co2_grid_kg`, `co2_avoided_indirect_kg` y `co2_avoided_direct_kg` de los traces de entrenamiento.
Con el criterio de mayor CO2 evitado total directo + indirecto, **A2C** lidera con **2,523,717 kg
CO2/año evitados** en el episodio trace 19. Esta lectura es complementaria: para el criterio OE3
canonico de menor F2/CO2 indirecto residual, **PPO** se mantiene como agente seleccionado.

## Inferencia estadistica

| Prueba | Resultado | Interpretacion |
|---|---:|---|
| Shapiro-Wilk SAC | W=0.536937, p=2.509e-11 | No normal |
| Shapiro-Wilk PPO | W=0.606314, p=2.420e-10 | No normal |
| Shapiro-Wilk A2C | W=0.834341, p=5.984e-06 | No normal |
| Kruskal-Wallis | H=53.023619, p=3.062e-12 | Hay diferencias entre agentes |
| Mann-Whitney U PPO < SAC | U=412, p=3.880e-09 | PPO emite menos que SAC |
| Mann-Whitney U PPO < A2C | U=746, p=2.592e-04 | PPO emite menos que A2C |
| Wilcoxon PPO < A2C | W=385, p=7.039e-03 | PPO conserva ventaja pareada sobre A2C |

## Archivos obsoletos

Los reportes binarios y figuras antiguas que declaraban SAC/A2C como seleccionados fueron retirados
o reemplazados. Si aparece una salida generada bajo `outputs/*_training/`, debe tratarse como artefacto
de entrenamiento, no como fuente canonica para informes.
