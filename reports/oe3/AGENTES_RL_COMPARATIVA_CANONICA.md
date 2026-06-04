# OE3 - Comparativa canonica de agentes RL

**Fecha de actualizacion:** 2026-05-31
**Decision vigente:** **A2C seleccionado**
**Alcance:** SAC v8.2 reentrenado el 2026-05-30/31 con VecNormalize; PPO y A2C vigentes del 2026-05-28. Reward `CO2_DUAL_FOCUS v8.1`, `obs_dim=19`, accion 3D y 50 episodios por agente.

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

- Si se usa solo el **menor F2 puntual**, gana **PPO** con 3,658,366 kg CO2/año en el episodio 26.
- Si se usa el **score multiobjetivo acumulado de 50 episodios** pedido para operacion, gana **A2C** porque lidera CO2 total evitado, importacion de red, conteo EV equivalente, BESS y violaciones.
- SAC fue el unico agente reentrenado en v8.2; ese reentrenamiento mejora SAC frente a su version anterior, pero no cambia los resultados guardados de PPO/A2C ni alcanza a A2C en el acumulado operativo.

## Tabla comparativa

| Rank | Agente | Criterios liderados | CO2 total evitado 50 ep (kg) | Grid import 50 ep (kWh) | CO2 directo 50 ep (kg) | CO2 indirecto 50 ep (kg) | EV equiv 50 ep | Motos 50 ep (kWh) | Mototaxis 50 ep (kWh) | BESS descarga 50 ep (kWh) | Deuda/violaciones | F2 minimo (kg/año) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **6/9** | **123,017,056** | 369,272,325 | 10,873,530 | 112,143,526 | 4,302,379 | 11,259,985 | 1,995,080 | 31,615,038 | 1,001 | 3,642,436 |
| 2 | PPO | 3/9 | 123,122,792 | 370,480,810 | 10,608,490 | 112,514,302 | 4,197,493 | 11,026,881 | 1,879,821 | 32,718,773 | 2,219 | 3,658,366 |
| 3 | SAC | 0/9 | 121,199,821 | 370,494,668 | 10,561,551 | 110,638,270 | 4,178,910 | 11,003,146 | 1,831,137 | 30,040,467 | 1,405 | 3,695,754 |

## Carga de motos y mototaxis en numeros

Los valores son conteos equivalentes de cargas completas, derivados del dataset vigente `data/interim/citylearn_v2/ev_charger_*.csv`.

| Agente | Motos equiv 50 ep | Mototaxis equiv 50 ep | Total equiv 50 ep | Promedio equiv/episodio |
|---|---:|---:|---:|---:|
| **A2C** | **3,875,653** | **426,726** | **4,302,379** | **86,048** |
| PPO | 3,795,419 | 402,074 | 4,197,493 | 83,950 |
| SAC | 3,787,250 | 391,661 | 4,178,910 | 83,578 |

A2C carga mas vehiculos equivalentes: +103,604 frente a PPO y +126,342 frente a SAC v8.2.

## Red, exportacion, violaciones y estabilidad

`solar_export_f6d` se estima desde `co2_f6d_kg / 0.4521`; los traces horarios no guardan `grid_export_kwh` de forma comparable para los tres agentes.

| Agente | Grid import 50 ep (kWh) | Solar export F6d 50 ep (kWh) | Violaciones total | Episodios sin violacion | CV plateau F2 | Reward validacion |
|---|---:|---:|---:|---:|---:|---:|
| **A2C** | **369,272,325** | **25,677,300** | **1,001** | 24 | 0.209% | 1647.04 |
| PPO | 370,480,810 | 26,272,265 | 2,219 | 37 | 0.054% | 1619.44 |
| SAC | 370,494,668 | 25,535,838 | 1,405 | 45 | 0.044% | 1520.92 |

Ningun agente termina los 50 episodios con cero violaciones acumuladas. A2C tiene la menor cantidad total de violaciones; SAC tiene mas episodios sin violacion, pero queda por debajo en CO2, red, carga EV y BESS. PPO es el mas estable por CV plateau, aunque no supera a A2C en el score operativo.
En validacion, A2C tambien obtiene el mayor reward medio y la menor importacion de red. SAC obtiene el mayor CO2 evitado medio de validacion, pero con menor reward, menor carga EV acumulada, menor BESS y mas violaciones que A2C en entrenamiento.

Recomendacion de produccion: implementar **A2C** como politica principal, con guardas de deuda de carga, limites operativos de BESS y monitoreo de grid import. PPO queda como referencia de estabilidad y F2 puntual; SAC v8.2 queda como respaldo experimental.

## Por que A2C gana

A2C lidera **6/9 criterios** del score multiobjetivo. Tambien tiene la mayor reduccion acumulada directa + indirecta en 50 episodios: **123,017,056 kg CO2**.
PPO reduce **-105,736 kg CO2** menos que A2C en el acumulado de 50 episodios.
SAC reduce **1,817,235 kg CO2** menos que A2C en el acumulado de 50 episodios.

Criterios liderados:

| Criterio | Direccion | Ganador | Valor |
|---|---|---|---:|
| Mayor CO2 total evitado | mayor | PPO | 123,122,792 |
| Menor importacion de red | menor | A2C | 369,272,325 |
| Mayor CO2 directo evitado | mayor | A2C | 10,873,530 |
| Mayor CO2 indirecto evitado | mayor | PPO | 112,514,302 |
| Mayor carga motos equivalentes | mayor | A2C | 3,875,653 |
| Mayor carga mototaxis equivalentes | mayor | A2C | 426,726 |
| Mayor carga EV total equivalente | mayor | A2C | 4,302,379 |
| Mayor uso util BESS | mayor | PPO | 32,718,773 |
| Menor deuda/violaciones de carga | menor | A2C | 1,001 |

SAC v8.2 mejoro despues de activar `VecNormalize` y ajustar hiperparametros, pero su reduccion acumulada es **121,199,821 kg CO2**, por debajo de A2C.

Lectura complementaria: PPO conserva el menor `F2` residual puntual (**3,658,366 kg CO2/año**, ep26), pero ese no es el criterio principal actualizado.

## Lectura complementaria desde trace

El reporte `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` calcula directamente las columnas `co2_grid_kg`, `co2_avoided_indirect_kg` y `co2_avoided_direct_kg` de los traces de entrenamiento.
Con el criterio de mayor CO2 evitado total directo + indirecto, **A2C** lidera con **2,519,848 kg CO2/año evitados** en el episodio trace 2.
Para el criterio OE3 canonico de menor F2/CO2 indirecto residual, **A2C** registra **3,642,436 kg CO2/año** en el episodio trace 2.

## Inferencia estadistica

Las pruebas se aplican sobre la serie por episodio de `co2_directa_kg + co2_indirecta_kg`.

| Prueba | Resultado | Interpretacion |
|---|---:|---|
| Shapiro-Wilk SAC | W=0.745803, p=6.072e-08 | No normal |
| Shapiro-Wilk PPO | W=0.794553, p=6.583e-07 | No normal |
| Shapiro-Wilk A2C | W=0.932862, p=7.103e-03 | No normal |
| Kruskal-Wallis | H=91.621955, p=1.272e-20 | Hay diferencias entre agentes |
| Mann-Whitney U A2C > PPO | U=947, p=9.818e-01 | A2C reduce mas que PPO |
| Mann-Whitney U A2C > SAC | U=2462, p=3.360e-17 | A2C reduce mas que SAC |
| Mann-Whitney U PPO > SAC | U=2417, p=4.432e-16 | PPO reduce mas que SAC |
| Wilcoxon A2C > PPO | W=447, p=9.676e-01 | Comparacion pareada A2C/PPO |
| Wilcoxon A2C > SAC | W=1275, p=8.882e-16 | Comparacion pareada A2C/SAC |
| F2 residual Kruskal-Wallis | H=54.203592, p=1.698e-12 | Referencia complementaria de CO2 residual |

## Archivos obsoletos

Los reportes binarios y figuras antiguas que declaraban SAC/A2C como seleccionados fueron retirados o reemplazados. Si aparece una salida generada bajo `outputs/*_training/`, debe tratarse como artefacto de entrenamiento, no como fuente canonica para informes.
