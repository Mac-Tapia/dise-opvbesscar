# OE3 - Auditoria de fuentes, checkpoints y resultados

**Fecha de actualizacion:** 2026-05-31

## Politica de fuentes

Se aceptan solo rutas vigentes de entrenamiento y checkpoints finales:

- `checkpoints/{AGENT}_CityLearn/{agent}_final.zip`
- `outputs/{agent}_training/result_{agent}.json`
- `outputs/{agent}_training/trace_{agent}.csv`
- `outputs/{agent}_training/{agent}_convergencia_episodios.csv`
- `outputs/{agent}_training/{agent}_episodios_history.csv`

No se usan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.

## Checkpoints y resultados auditados

| Agente | Timestamp result | Checkpoint final | Result JSON | Trace filas | Episodios trace completos | Filas parciales ignoradas | Estado |
|---|---|---|---|---:|---:|---:|---|
| SAC | 20260530_221733 | `checkpoints/SAC_CityLearn/sac_final.zip` | `outputs/sac_training/result_sac.json` | 438,000 | 50 | 0 | vigente/no archive |
| PPO | 20260528_083447 | `checkpoints/PPO_CityLearn/ppo_final.zip` | `outputs/ppo_training/result_ppo.json` | 438,272 | 50 | 272 | vigente/no archive |
| A2C | 20260528_090107 | `checkpoints/A2C_CityLearn/a2c_final.zip` | `outputs/a2c_training/result_a2c.json` | 438,272 | 50 | 272 | vigente/no archive |

## Resultado guardado vigente

| Agente | F2 minimo | Episodio F2 | CO2 evitado vs F0 | CV plateau | Reward validacion | Grid validacion |
|---|---:|---:|---:|---:|---:|---:|
| SAC | 3,693,084 | 17 | 3,360,916 | 0.036% | 1,517.13 | 7,345,854 |
| PPO | 3,657,484 | 49 | 3,396,516 | 0.034% | 1,628.46 | 7,348,969 |
| A2C | 3,659,010 | 45 | 3,394,990 | 0.422% | 1,633.29 | 7,337,811 |

## Score multiobjetivo acumulado 50 episodios

| Agente | Criterios liderados | CO2 total evitado | Grid import | EV equiv 50 ep | BESS descarga | Deuda/violaciones |
|---|---:|---:|---:|---:|---:|---:|
| A2C | 9/9 | 122,980,987 | 368,798,317 | 4,307,304 | 33,504,412 | 811 |
| PPO | 0/9 | 122,688,120 | 370,717,132 | 4,203,700 | 31,831,147 | 2,333 |
| SAC | 0/9 | 121,316,857 | 370,440,348 | 4,180,962 | 30,022,939 | 1,385 |

## Lectura trace complementaria

| Criterio trace | SAC | PPO | A2C | Ganador parcial |
|---|---:|---:|---:|---|
| CO2 total evitado maximo | 2,434,161 | 2,469,954 | 2,523,717 | A2C |
| CO2 directo evitado maximo | 220,168 | 227,155 | 225,136 | PPO |
| CO2 indirecto evitado maximo | 2,286,741 | 2,365,179 | 2,377,543 | A2C |
| CO2 indirecto residual minimo | 3,693,084 | 3,657,484 | 3,659,010 | PPO |

## Conclusion de auditoria

El SAC auditado corresponde al checkpoint final vigente `checkpoints/SAC_CityLearn/sac_final.zip`; no se usaron checkpoints antiguos ni archivos archivados. Con el criterio multiobjetivo acumulado de 50 episodios, A2C lidera 9/9 criterios: mayor CO2 directo+indirecto evitado, menor importacion de red, mayor carga equivalente de motos/mototaxis, mayor uso util de BESS y menor deuda/violaciones de carga.

PPO conserva el menor F2 residual puntual, pero esa lectura queda como criterio complementario y no reemplaza el score multiobjetivo acumulado. SAC fue el unico reentrenado en v8.2; mejoro frente a su version anterior, pero no supera a A2C.

- JSON: `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.json`
