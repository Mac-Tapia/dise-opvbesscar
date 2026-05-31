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

`F2` se mantiene como lectura complementaria de CO2 residual minimo, pero no reemplaza la seleccion multiobjetivo. La prueba de normalidad solo decide el tipo de inferencia; no elige el agente.

## Tabla comparativa

| Rank | Agente | Criterios liderados | CO2 total evitado 50 ep (kg) | Grid import 50 ep (kWh) | CO2 directo 50 ep (kg) | CO2 indirecto 50 ep (kg) | Motos 50 ep (kWh) | Mototaxis 50 ep (kWh) | BESS descarga 50 ep (kWh) | Deuda/violaciones | F2 minimo (kg/año) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | 368,798,317 | 10,885,952 | 112,095,035 | 11,247,831 | 2,037,664 | 33,504,412 | 811 | 3,659,010 |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 10,624,191 | 112,063,929 | 11,056,358 | 1,861,407 | 31,831,147 | 2,333 | 3,657,484 |
| 3 | SAC | 0/9 | 121,316,857 | 370,440,348 | 10,566,738 | 110,750,119 | 11,009,496 | 1,830,512 | 30,022,939 | 1,385 | 3,693,084 |

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
| Mayor carga motos | mayor | A2C | 11,247,831 |
| Mayor carga mototaxis | mayor | A2C | 2,037,664 |
| Mayor carga EV total | mayor | A2C | 13,285,495 |
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
