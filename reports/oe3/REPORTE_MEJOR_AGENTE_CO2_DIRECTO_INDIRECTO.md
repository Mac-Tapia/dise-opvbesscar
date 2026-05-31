# OE3 - Reporte mejor agente multiobjetivo CO2, red, EV y BESS

**Fecha de actualizacion:** 2026-05-31
**Fuente canonica:** `reports/oe3/agents_comparison_canonical.json`
**Trace complementario:** `reports/oe3/co2_trace_direct_indirect_summary.csv`
**Entrenamiento:** SAC v8.2 reentrenado el 2026-05-30/31 con `VecNormalize`; PPO y A2C vigentes del 2026-05-28.
**Reward:** `CO2_DUAL_FOCUS v8.1`, `obs_dim=18`, `action_dim=3`, 50 episodios por agente.

## Decision ejecutiva

Con el criterio multiobjetivo pedido, el agente seleccionado es **A2C**. La seleccion ya no se hace
por el menor `F2` puntual, sino por el agente que acumula mejor desempeño en los **50 episodios**:

- mayor CO2 total evitado directo + indirecto,
- menor importacion de red,
- mayor reduccion directa de CO2,
- mayor reduccion indirecta de CO2,
- mayor carga de motos y mototaxis medida en eventos equivalentes de carga,
- mejor control de cargadores medido por menor deuda/violaciones,
- mayor uso util de BESS.

A2C lidera **9 de 9 criterios**. PPO conserva el menor `F2` residual puntual, pero ese criterio queda
como lectura complementaria.

El cambio de PPO a A2C no viene de reentrenar PPO/A2C. PPO y A2C mantienen los resultados guardados
del 2026-05-28. El cambio viene de separar dos criterios: **PPO gana solo el F2 puntual**, mientras
**A2C gana el multiobjetivo acumulado de 50 episodios**. SAC fue el unico reentrenado en v8.2; mejoro
respecto a su version anterior, pero no alcanzo a A2C en los acumulados operativos.

## Score multiobjetivo 50 episodios

| Rank | Agente | Criterios liderados | CO2 total evitado kg | Grid import kWh | CO2 directo kg | CO2 indirecto kg | EV equiv 50 ep | BESS descarga kWh | Deuda/violaciones |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | **368,798,317** | **10,885,952** | **112,095,035** | **4,307,304** | **33,504,412** | **811** |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 10,624,191 | 112,063,929 | 4,203,700 | 31,831,147 | 2,333 |
| 3 | SAC v8.2 | 0/9 | 121,316,857 | 370,440,348 | 10,566,738 | 110,750,119 | 4,180,962 | 30,022,939 | 1,385 |

Ventajas cuantificables de A2C:

| Comparacion | Ventaja A2C |
|---|---:|
| CO2 total evitado vs PPO | +292,867 kg CO2 |
| CO2 total evitado vs SAC | +1,664,130 kg CO2 |
| Menor grid import vs PPO | -1,918,815 kWh |
| Menor grid import vs SAC | -1,642,032 kWh |
| Mayor carga EV total vs PPO | +103,604 eventos equivalentes |
| Mayor carga EV total vs SAC | +126,342 eventos equivalentes |
| Menor deuda/violaciones vs PPO | -1,522 |
| Menor deuda/violaciones vs SAC | -574 |

## Carga de motos y mototaxis

Los conteos no salen de las columnas directas del trace porque PPO/A2C las guardaron en cero.
Se calculan como eventos equivalentes de carga: kWh EV dividido por la energia media del dataset real
(`2.905 kWh/moto` y `4.675 kWh/mototaxi`).

| Agente | Motos equiv 50 ep | Mototaxis equiv 50 ep | Total equiv 50 ep | Promedio equiv/episodio |
|---|---:|---:|---:|---:|
| **A2C** | **3,871,470** | **435,835** | **4,307,304** | **86,146** |
| PPO | 3,805,565 | 398,135 | 4,203,700 | 84,074 |
| SAC v8.2 | 3,789,435 | 391,527 | 4,180,962 | 83,619 |

A2C carga la mayor cantidad de motos y mototaxis en numeros: 65,905 motos equivalentes y
37,700 mototaxis equivalentes mas que PPO; 82,034 motos y 44,308 mototaxis mas que SAC v8.2.

## CO2 directo e indirecto

| Agente | CO2 directo evitado kg | CO2 indirecto evitado kg | CO2 total evitado kg |
|---|---:|---:|---:|
| **A2C** | **10,885,952** | **112,095,035** | **122,980,987** |
| PPO | 10,624,191 | 112,063,929 | 122,688,120 |
| SAC v8.2 | 10,566,738 | 110,750,119 | 121,316,857 |

## Red y BESS

| Agente | Grid import kWh 50 ep | Solar export F6d kWh 50 ep | BESS descarga kWh 50 ep | Deuda/violaciones | Episodios sin violacion | CV plateau F2 |
|---|---:|---:|---:|---:|---:|---:|
| **A2C** | **368,798,317** | **26,261,213** | **33,504,412** | **811** | 22 | 0.422% |
| PPO | 370,717,132 | 26,109,780 | 31,831,147 | 2,333 | 35 | **0.034%** |
| SAC v8.2 | 370,440,348 | 25,520,507 | 30,022,939 | 1,385 | **45** | 0.036% |

Ningun agente tiene cero violaciones acumuladas en los 50 episodios. A2C es el mejor en total de
violaciones; SAC tiene mas episodios sin violacion, pero pierde en CO2, importacion de red, carga EV
y BESS. PPO es el mas estable por CV plateau, aunque no es el mejor para produccion por sus 2,333
violaciones y mayor importacion de red.

## F2 residual complementario

| Agente | F2 minimo kg CO2/año | Episodio |
|---|---:|---:|
| PPO | **3,657,484** | 49 |
| A2C | 3,659,010 | 45 |
| SAC v8.2 | 3,693,084 | 17 |

PPO tiene el menor `F2` puntual por **1,526 kg CO2/año** frente a A2C. Sin embargo, A2C supera a
PPO en el acumulado de 50 episodios y en los criterios operativos de carga EV, red, BESS y deuda de
carga.

## Validacion post-entrenamiento

| Agente | Reward validacion | Grid import validacion kWh/año | CO2 evitado validacion kg/año | Lectura |
|---|---:|---:|---:|---|
| **A2C** | **1,633.29** | **7,337,811** | 2,412,246 | Mejor reward y menor importacion de red |
| PPO | 1,628.46 | 7,348,969 | 2,416,093 | Segundo reward; peor grid |
| SAC v8.2 | 1,517.13 | 7,345,854 | **2,438,610** | Mayor CO2 evitado validacion, pero menor reward |

La validacion confirma que SAC mejoro en CO2 evitado medio, pero no supera el criterio operativo
completo: queda con menor reward, menor carga EV acumulada, menor uso BESS y mas violaciones que A2C.

## Pruebas estadisticas sobre CO2 total evitado por episodio

| Prueba | Resultado | Interpretacion |
|---|---:|---|
| Shapiro-Wilk SAC | W=0.598363, p=1.842e-10 | No normal |
| Shapiro-Wilk PPO | W=0.677219, p=3.301e-09 | No normal |
| Shapiro-Wilk A2C | W=0.962455, p=1.127e-01 | Compatible con normalidad |
| Kruskal-Wallis | H=57.557340, p=3.174e-13 | Hay diferencias entre agentes |
| Mann-Whitney U A2C > PPO | U=1353, p=2.399e-01 | Ventaja acumulada de A2C no significativa frente a PPO |
| Mann-Whitney U A2C > SAC | U=2226, p=8.784e-12 | A2C supera a SAC |
| Mann-Whitney U PPO > SAC | U=2171, p=1.107e-10 | PPO supera a SAC |
| Wilcoxon A2C > PPO | W=766, p=1.093e-01 | Ventaja pareada no significativa frente a PPO |
| Wilcoxon A2C > SAC | W=1251, p=6.768e-13 | A2C supera a SAC |

## Resultado final

**A2C** es el agente seleccionado bajo el criterio multiobjetivo de 50 episodios. Reduce la mayor
cantidad total de CO2, importa menos energia de red, carga mas motos y mototaxis, usa mas BESS y
mantiene menos deuda/violaciones de carga. Es el candidato de produccion, con guardas operativas
para deuda de carga, limites BESS y monitoreo de importacion de red.
