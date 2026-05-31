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
- mayor carga de motos y mototaxis,
- mejor control de cargadores medido por menor deuda/violaciones,
- mayor uso util de BESS.

A2C lidera **9 de 9 criterios**. PPO conserva el menor `F2` residual puntual, pero ese criterio queda
como lectura complementaria.

## Score multiobjetivo 50 episodios

| Rank | Agente | Criterios liderados | CO2 total evitado kg | Grid import kWh | CO2 directo kg | CO2 indirecto kg | EV total kWh | BESS descarga kWh | Deuda/violaciones |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | **368,798,317** | **10,885,952** | **112,095,035** | **13,285,495** | **33,504,412** | **811** |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 10,624,191 | 112,063,929 | 12,917,765 | 31,831,147 | 2,333 |
| 3 | SAC v8.2 | 0/9 | 121,316,857 | 370,440,348 | 10,566,738 | 110,750,119 | 12,840,008 | 30,022,939 | 1,385 |

Ventajas cuantificables de A2C:

| Comparacion | Ventaja A2C |
|---|---:|
| CO2 total evitado vs PPO | +292,867 kg CO2 |
| CO2 total evitado vs SAC | +1,664,130 kg CO2 |
| Menor grid import vs PPO | -1,918,815 kWh |
| Menor grid import vs SAC | -1,642,032 kWh |
| Mayor carga EV total vs PPO | +367,730 kWh |
| Mayor carga EV total vs SAC | +445,487 kWh |
| Menor deuda/violaciones vs PPO | -1,522 |
| Menor deuda/violaciones vs SAC | -574 |

## Carga de motos y mototaxis

| Agente | Motos kWh 50 ep | Mototaxis kWh 50 ep | EV total kWh 50 ep |
|---|---:|---:|---:|
| **A2C** | **11,247,831** | **2,037,664** | **13,285,495** |
| PPO | 11,056,358 | 1,861,407 | 12,917,765 |
| SAC v8.2 | 11,009,496 | 1,830,512 | 12,840,008 |

## CO2 directo e indirecto

| Agente | CO2 directo evitado kg | CO2 indirecto evitado kg | CO2 total evitado kg |
|---|---:|---:|---:|
| **A2C** | **10,885,952** | **112,095,035** | **122,980,987** |
| PPO | 10,624,191 | 112,063,929 | 122,688,120 |
| SAC v8.2 | 10,566,738 | 110,750,119 | 121,316,857 |

## Red y BESS

| Agente | Grid import kWh 50 ep | BESS descarga kWh 50 ep | Deuda/violaciones |
|---|---:|---:|---:|
| **A2C** | **368,798,317** | **33,504,412** | **811** |
| SAC v8.2 | 370,440,348 | 30,022,939 | 1,385 |
| PPO | 370,717,132 | 31,831,147 | 2,333 |

## F2 residual complementario

| Agente | F2 minimo kg CO2/año | Episodio |
|---|---:|---:|
| PPO | **3,657,484** | 49 |
| A2C | 3,659,010 | 45 |
| SAC v8.2 | 3,693,084 | 17 |

PPO tiene el menor `F2` puntual por **1,526 kg CO2/año** frente a A2C. Sin embargo, A2C supera a
PPO en el acumulado de 50 episodios y en los criterios operativos de carga EV, red, BESS y deuda de
carga.

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
mantiene menos deuda/violaciones de carga.
