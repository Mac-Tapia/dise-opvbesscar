# OE3 - Reporte mejor agente por CO2 directo, indirecto y control electrico

**Fecha de actualizacion:** 2026-05-31
**Fuente canonica:** `reports/oe3/agents_comparison_canonical.json`
**Trace complementario:** `reports/oe3/co2_trace_direct_indirect_summary.csv`
**Entrenamiento:** SAC v8.2 reentrenado el 2026-05-30/31 con `VecNormalize`; PPO y A2C vigentes del 2026-05-28.
**Reward:** `CO2_DUAL_FOCUS v8.1`, `obs_dim=18`, `action_dim=3`, 50 episodios por agente.

## Decision ejecutiva

El mejor agente OE3 bajo el criterio canonico de control ambiental es **PPO**. Su mejor episodio
reduce el CO2 indirecto residual `F2` a **3,657,484 kg CO2/año** en el episodio **49**.

La lectura directa desde trace confirma dos matices importantes:

- **PPO** tambien gana en menor CO2 indirecto emitido por red: **3,657,484 kg CO2/año**.
- **A2C** gana si el criterio aislado es maximo CO2 total evitado directo + indirecto:
  **2,523,717 kg CO2/año** en el episodio trace 19.
- **SAC v8.2** mejoro frente al SAC anterior, pero no supera a PPO/A2C en `F2`.

La prueba de normalidad no selecciona el agente. Shapiro-Wilk solo justifica usar pruebas no
parametricas; la seleccion se hace por metricas operativas: menor `F2`, CO2 evitado, importacion de
red, cumplimiento EV y convergencia.

## Ranking canonico por F2

| Rank | Agente | F2 minimo kg CO2/año | Episodio | F2 media kg/año | CO2 evitado vs F0 | Reduccion vs F0 | CV plateau | Reward validacion | Grid validacion kWh |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | **3,657,484** | **49** | 3,695,605 | **3,396,515** | **48.15%** | **0.034%** | 1,628.46 | 7,348,969 |
| 2 | A2C | 3,659,010 | 45 | 3,699,834 | 3,394,989 | 48.13% | 0.422% | 1,633.29 | **7,337,811** |
| 3 | SAC v8.2 | 3,693,084 | 17 | 3,711,823 | 3,360,915 | 47.65% | 0.036% | 1,517.13 | 7,345,854 |

PPO gana por **1,526 kg CO2/año** frente a A2C y por **35,600 kg CO2/año** frente a SAC v8.2.
A2C mantiene la menor importacion de red en validacion, pero su `F2` minimo queda ligeramente por
encima de PPO.

## CO2 directo e indirecto desde trace

| Criterio trace | Ganador | Episodio | Valor kg CO2/año | PPO | A2C | SAC v8.2 |
|---|---|---:|---:|---:|---:|---:|
| Maximo CO2 total evitado directo + indirecto | A2C | 19 | 2,523,717 | 2,469,954 | **2,523,717** | 2,434,161 |
| Maximo CO2 directo evitado | PPO | 48 | 227,155 | **227,155** | 225,136 | 220,168 |
| Maximo CO2 indirecto evitado | A2C | 1 | 2,377,543 | 2,365,179 | **2,377,543** | 2,286,741 |
| Minimo CO2 indirecto emitido por red | PPO | 49 | 3,657,484 | **3,657,484** | 3,659,010 | 3,693,084 |

Esta tabla explica por que puede aparecer A2C como lider en CO2 evitado total desde trace, mientras
PPO sigue siendo el agente seleccionado: OE3 prioriza el menor CO2 residual operativo (`F2`), no solo
la suma de CO2 evitado.

## Diagnostico SAC v8.2

SAC no perdio por usar datos antiguos. La verificacion de `training_validation.py`, el wrapper
CityLearn y los resultados guardados confirman que usa los mismos datos reales actuales que PPO/A2C:
`data/iquitos_ev_mall/` y `data/interim/citylearn_v2/`.

El problema del SAC anterior era principalmente de regimen de entrenamiento:

- No usaba `VecNormalize`; PPO/A2C si normalizaban observaciones y retornos.
- `gamma=0.99` era demasiado largo para episodios anuales de 8,760 pasos.
- El replay buffer conservaba transiciones tempranas suboptimas.
- La exploracion de `ent_coef="auto"` y `target_entropy=-3.0` convergia a una politica conservadora.
- La arquitectura de critic era menor que la usada por PPO/A2C.

Los ajustes aplicados en SAC v8.2 fueron:

| Parametro | SAC anterior | SAC v8.2 |
|---|---:|---:|
| Normalizacion entorno | No | `VecNormalize(norm_obs=True, norm_reward=True)` |
| `learning_rate` | `5e-5` | `1e-4` |
| `buffer_size` | `100000` | `87600` |
| `learning_starts` | `8760` | `17520` |
| `batch_size` | `256` | `512` en CUDA |
| `gamma` | `0.99` | `0.95` |
| `gradient_steps` | `1` | `2` |
| `ent_coef` | `auto` | `auto_0.2` |
| `target_entropy` | `-3.0` | `-2.0` |
| Critic | `[256,256]` | `qf=[512,512,256]` |

## Resultado SAC antes vs despues

| Version SAC | Mejor F2 kg CO2/año | Episodio | Reward validacion | CO2 evitado validacion kg | Grid validacion kWh | Estado |
|---|---:|---:|---:|---:|---:|---|
| SAC anterior archivado | 3,720,640 | 33 | 1,519.15 | 2,400,665 | 7,456,699 | Resultado/traces archivados; checkpoints archivados eliminados |
| SAC v8.2 actual | **3,693,084** | **17** | 1,517.13 | **2,438,610** | **7,345,854** | Checkpoint final vigente + `vecnormalize.pkl` |

Mejoras de SAC v8.2 frente al SAC anterior:

- `F2` baja **27,556 kg CO2/año**.
- Grid import de validacion baja **110,845 kWh/año**.
- CO2 evitado de validacion sube **37,944 kg CO2/año**.
- La convergencia queda estable: `CV plateau = 0.036%`.

La mejora es real, pero no alcanza para ganar: SAC v8.2 queda **35,600 kg CO2/año** por encima de
PPO en `F2`.

## Estado de checkpoints y archivos

- Checkpoints SAC archivados anteriores: eliminados por instruccion del usuario.
- Checkpoints PPO/A2C: no se tocaron.
- SAC vigente: `checkpoints/SAC_CityLearn/sac_final.zip`.
- Normalizacion SAC vigente: `checkpoints/SAC_CityLearn/vecnormalize.pkl`.
- Resultado SAC vigente: `outputs/sac_training/result_sac.json`.
- Trace SAC vigente: `outputs/sac_training/trace_sac.csv`.

## Veredicto final

| Criterio | Mejor agente | Justificacion |
|---|---|---|
| Seleccion canonica OE3 | **PPO** | Menor `F2`: 3,657,484 kg CO2/año |
| CO2 total evitado desde trace | A2C | Mayor suma directa + indirecta: 2,523,717 kg CO2/año |
| CO2 directo evitado | PPO | 227,155 kg CO2/año |
| Menor importacion de red en validacion | A2C | 7,337,811 kWh/año |
| SAC mejorado | No seleccionado | Mejoro, pero su `F2` sigue +35,600 kg CO2/año sobre PPO |

**Conclusion:** para informes y consultas de otros agentes debe usarse **PPO** como agente OE3
seleccionado. A2C puede citarse como mejor en CO2 total evitado desde trace y en grid validation,
pero no reemplaza a PPO en el criterio canonico de menor CO2 residual.
