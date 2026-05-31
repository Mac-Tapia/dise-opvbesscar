# Documentos vigentes OE2 y OE3

**Actualizado:** 2026-05-30
**Estado:** indice canonico para consultas de informes y agentes externos.

## OE3 - Control RL

El resultado vigente de seleccion de agente es **PPO**. Los documentos antiguos que indicaban SAC o A2C
como ganador son historicos y no deben usarse para reportes nuevos.

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` | Informe principal de comparativa SAC/PPO/A2C y seleccion PPO |
| 2 | `reports/oe3/agents_comparison_canonical.json` | Fuente estructurada para consultas desde otros agentes |
| 3 | `reports/oe3/agents_comparison_canonical.csv` | Tabla comparativa para hojas de calculo/reportes |
| 4 | `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md` | Auditoria de checkpoints finales y resultados guardados vigentes |
| 5 | `reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md` | Informe operativo CO2 directo/indirecto, eficiencia y convergencia |
| 6 | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` | Reporte trace de CO2 directo e indirecto |
| 7 | `reports/oe3/co2_trace_direct_indirect_summary.json` | Fuente estructurada del analisis trace CO2 directo/indirecto |
| 8 | `outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json` | Resumen estadistico no parametrico actualizado |

Resumen vigente:

| Rank | Agente | F2 minimo (kg CO2/año) | Episodio | Reduccion vs F0 |
|---:|---|---:|---:|---:|
| 1 | **PPO** | **3,657,483** | **49** | **48.15%** |
| 2 | A2C | 3,659,010 | 45 | 48.13% |
| 3 | SAC | 3,720,640 | 33 | 47.25% |

Lectura complementaria desde `trace`: por CO2 evitado total directo + indirecto, A2C lidera
con 2,523,717 kg CO2/año evitados en el episodio trace 19. Esta lectura no reemplaza el criterio
canonico F2, donde PPO sigue siendo el agente seleccionado por menor CO2 indirecto emitido.

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
