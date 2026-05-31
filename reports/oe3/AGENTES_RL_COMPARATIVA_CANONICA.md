# OE3 - Comparativa canonica de agentes RL

**Fecha de actualizacion:** 2026-05-31
**Decision vigente:** **A2C seleccionado**
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

El criterio principal actualizado de OE3 es un **score multiobjetivo de 50 episodios**. Se cuentan los liderazgos por criterio: mayor CO2 total evitado, menor importacion de red, mayor CO2 directo evitado, mayor CO2 indirecto evitado, mayor carga de motos/mototaxis, mayor uso util de BESS y menor deuda/violaciones de carga.
Para motos y mototaxis se reportan **eventos de carga equivalentes**, no solo kWh: los kWh EV de cada agente se dividen por la energia media por vehiculo del dataset real (2.905 kWh/moto y 4.675 kWh/mototaxi). Las columnas directas de conteo en trace no se usan para comparar porque PPO/A2C las guardaron en cero.

`F2` se mantiene como lectura complementaria de CO2 residual minimo, pero no reemplaza la seleccion multiobjetivo. La prueba de normalidad solo decide el tipo de inferencia; no elige el agente.

## Por que cambio de PPO a A2C

La comparacion no cambio porque PPO o A2C se hayan reentrenado; PPO y A2C siguen usando los resultados vigentes del 2026-05-28. Lo que cambio fue el criterio de decision:

- Si se usa solo el **menor F2 puntual**, gana **PPO** con 3,657,484 kg CO2/año en el episodio 49.
- Si se usa el **score multiobjetivo acumulado de 50 episodios** pedido para operacion, gana **A2C** porque lidera CO2 total evitado, importacion de red, conteo EV equivalente, BESS y violaciones.
- SAC fue el unico agente reentrenado en v8.2; ese reentrenamiento mejora SAC frente a su version anterior, pero no cambia los resultados guardados de PPO/A2C ni alcanza a A2C en el acumulado operativo.

## Tabla comparativa

| Rank | Agente | Criterios liderados | CO2 total evitado 50 ep (kg) | Grid import 50 ep (kWh) | CO2 directo 50 ep (kg) | CO2 indirecto 50 ep (kg) | EV equiv 50 ep | Motos 50 ep (kWh) | Mototaxis 50 ep (kWh) | BESS descarga 50 ep (kWh) | Deuda/violaciones | F2 minimo (kg/año) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | 368,798,317 | 10,885,952 | 112,095,035 | 4,307,304 | 11,247,831 | 2,037,664 | 33,504,412 | 811 | 3,659,010 |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 10,624,191 | 112,063,929 | 4,203,700 | 11,056,358 | 1,861,407 | 31,831,147 | 2,333 | 3,657,484 |
| 3 | SAC | 0/9 | 121,316,857 | 370,440,348 | 10,566,738 | 110,750,119 | 4,180,962 | 11,009,496 | 1,830,512 | 30,022,939 | 1,385 | 3,693,084 |

## Carga de motos y mototaxis en numeros

Los valores son conteos equivalentes de cargas completas, derivados del dataset vigente `data/interim/citylearn_v2/ev_charger_*.csv`.

| Agente | Motos equiv 50 ep | Mototaxis equiv 50 ep | Total equiv 50 ep | Promedio equiv/episodio |
|---|---:|---:|---:|---:|
| **A2C** | **3,871,470** | **435,835** | **4,307,304** | **86,146** |
| PPO | 3,805,565 | 398,135 | 4,203,700 | 84,074 |
| SAC | 3,789,435 | 391,527 | 4,180,962 | 83,619 |

A2C carga mas vehiculos equivalentes: +103,604 frente a PPO y +126,342 frente a SAC v8.2.

## Red, exportacion, violaciones y estabilidad

`solar_export_f6d` se estima desde `co2_f6d_kg / 0.4521`; los traces horarios no guardan `grid_export_kwh` de forma comparable para los tres agentes.

| Agente | Grid import 50 ep (kWh) | Solar export F6d 50 ep (kWh) | Violaciones total | Episodios sin violacion | CV plateau F2 | Reward validacion |
|---|---:|---:|---:|---:|---:|---:|
| **A2C** | **368,798,317** | **26,261,213** | **811** | 22 | 0.422% | 1633.29 |
| PPO | 370,717,132 | 26,109,780 | 2,333 | 35 | 0.034% | 1628.46 |
| SAC | 370,440,348 | 25,520,507 | 1,385 | 45 | 0.036% | 1517.13 |

Ningun agente termina los 50 episodios con cero violaciones acumuladas. A2C tiene la menor cantidad total de violaciones; SAC tiene mas episodios sin violacion, pero queda por debajo en CO2, red, carga EV y BESS. PPO es el mas estable por CV plateau, aunque no supera a A2C en el score operativo.
En validacion, A2C tambien obtiene el mayor reward medio y la menor importacion de red. SAC obtiene el mayor CO2 evitado medio de validacion, pero con menor reward, menor carga EV acumulada, menor BESS y mas violaciones que A2C en entrenamiento.

Recomendacion de produccion: implementar **A2C** como politica principal, con guardas de deuda de carga, limites operativos de BESS y monitoreo de grid import. PPO queda como referencia de estabilidad y F2 puntual; SAC v8.2 queda como respaldo experimental.

## Por que A2C gana

A2C lidera **9/9 criterios** del score multiobjetivo. Tambien tiene la mayor reduccion acumulada directa + indirecta en 50 episodios: **122,980,987 kg CO2**.
PPO reduce **292,867 kg CO2** menos que A2C en el acumulado de 50 episodios.
SAC reduce **1,664,130 kg CO2** menos que A2C en el acumulado de 50 episodios.

Criterios liderados:

| Criterio | Direccion | Ganador | Valor |
|---|---|---|---:|
| Mayor CO2 total evitado | mayor | A2C | 122,980,987 |
| Menor importacion de red | menor | A2C | 368,798,317 |
| Mayor CO2 directo evitado | mayor | A2C | 10,885,952 |
| Mayor CO2 indirecto evitado | mayor | A2C | 112,095,035 |
| Mayor carga motos equivalentes | mayor | A2C | 3,871,470 |
| Mayor carga mototaxis equivalentes | mayor | A2C | 435,835 |
| Mayor carga EV total equivalente | mayor | A2C | 4,307,304 |
| Mayor uso util BESS | mayor | A2C | 33,504,412 |
| Menor deuda/violaciones de carga | menor | A2C | 811 |

SAC v8.2 mejoro despues de activar `VecNormalize` y ajustar hiperparametros, pero su reduccion acumulada es **121,316,857 kg CO2**, por debajo de A2C.

Lectura complementaria: PPO conserva el menor `F2` residual puntual (**3,657,484 kg CO2/año**, ep49), pero ese no es el criterio principal actualizado.

## Lectura complementaria desde trace

El reporte `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` calcula directamente las columnas `co2_grid_kg`, `co2_avoided_indirect_kg` y `co2_avoided_direct_kg` de los traces de entrenamiento.
Con el criterio de mayor CO2 evitado total directo + indirecto, **A2C** lidera con **2,523,717 kg CO2/año evitados** en el episodio trace 19.
Para el criterio OE3 canonico de menor F2/CO2 indirecto residual, **PPO** registra **3,657,484 kg CO2/año** en el episodio trace 49.

## Inferencia estadistica

Las pruebas se aplican sobre la serie por episodio de `co2_directa_kg + co2_indirecta_kg`.

| Prueba | Resultado | Interpretacion |
|---|---:|---|
| Shapiro-Wilk SAC | W=0.598363, p=1.842e-10 | No normal |
| Shapiro-Wilk PPO | W=0.677219, p=3.301e-09 | No normal |
| Shapiro-Wilk A2C | W=0.962455, p=1.127e-01 | Normal |
| Kruskal-Wallis | H=57.557340, p=3.174e-13 | Hay diferencias entre agentes |
| Mann-Whitney U A2C > PPO | U=1353, p=2.399e-01 | A2C reduce mas que PPO |
| Mann-Whitney U A2C > SAC | U=2226, p=8.784e-12 | A2C reduce mas que SAC |
| Mann-Whitney U PPO > SAC | U=2171, p=1.107e-10 | PPO reduce mas que SAC |
| Wilcoxon A2C > PPO | W=766, p=1.093e-01 | Comparacion pareada A2C/PPO |
| Wilcoxon A2C > SAC | W=1251, p=6.768e-13 | Comparacion pareada A2C/SAC |
| F2 residual Kruskal-Wallis | H=30.593505, p=2.274e-07 | Referencia complementaria de CO2 residual |

## Archivos obsoletos

Los reportes binarios y figuras antiguas que declaraban SAC/A2C como seleccionados fueron retirados o reemplazados. Si aparece una salida generada bajo `outputs/*_training/`, debe tratarse como artefacto de entrenamiento, no como fuente canonica para informes.
