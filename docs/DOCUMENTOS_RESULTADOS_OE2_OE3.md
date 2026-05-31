# Documentos vigentes OE2 y OE3

**Actualizado:** 2026-05-31
**Estado:** indice canonico para consultas de informes y agentes externos.

## OE3 - Control RL

El resultado vigente de seleccion de agente es **A2C** bajo el score multiobjetivo acumulado de
50 episodios. SAC fue reentrenado en v8.2 con `VecNormalize` el 2026-05-30/31, pero no supera a A2C
en CO2 total evitado, grid import, carga EV, BESS ni deuda/violaciones.

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` | Informe principal de comparativa SAC/PPO/A2C y seleccion A2C |
| 2 | `reports/oe3/agents_comparison_canonical.json` | Fuente estructurada para consultas desde otros agentes |
| 3 | `reports/oe3/agents_comparison_canonical.csv` | Tabla comparativa para hojas de calculo/reportes |
| 4 | `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md` | Auditoria de checkpoints finales y resultados guardados vigentes |
| 5 | `reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md` | Informe operativo CO2 directo/indirecto, eficiencia y convergencia |
| 6 | `reports/oe3/DIAGNOSTICO_SAC_PLAN_REENTRENAMIENTO.md` | Diagnostico de SAC v8.2, mejoras y plan siguiente |
| 7 | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` | Reporte trace de CO2 directo e indirecto |
| 8 | `reports/oe3/co2_trace_direct_indirect_summary.json` | Fuente estructurada del analisis trace CO2 directo/indirecto |
| 9 | `outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json` | Resumen estadistico no parametrico actualizado |

Resumen vigente:

| Rank | Agente | Criterios liderados | CO2 total evitado kg | Grid import kWh | EV total kWh | Deuda/violaciones |
|---:|---|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | **368,798,317** | **13,285,495** | **811** |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 12,917,765 | 2,333 |
| 3 | SAC v8.2 | 0/9 | 121,316,857 | 370,440,348 | 12,840,008 | 1,385 |

Lectura complementaria: PPO conserva el menor F2 puntual con 3,657,484 kg CO2/año en el episodio 49,
pero no reemplaza el criterio multiobjetivo acumulado.

## OE2 - Dimensionamiento

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md` | Verificacion vigente de correcciones OE2 v5.2 actualizadas al pipeline v5.8 |
| 2 | `data/oe2/Generacionsolar/informe_generacion_solar_procedimiento_resultados_descriptivos.md` | Procedimiento y resultados descriptivos de generacion solar |
| 3 | `data/iquitos_ev_mall/dataset_config_v7.json` | Configuracion CityLearn v2 validada |

## Artefactos retirados o reemplazados

Se retiraron de Git los binarios y figuras de reportes OE3 que contenian resultados anteriores:

- `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v10.docx`
- `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v11.docx`
- `outputs/hypothesis_test/hypothesis_test_co2_figura_completa.png`
- duplicados HTML/PDF de arquitectura que declaraban SAC como ganador.

Las salidas locales de entrenamiento bajo `outputs/*_training/` y `outputs/seccion52/` son artefactos
generados. No deben tratarse como documentos canónicos salvo que se consoliden en `reports/oe3/`.
