# Documentos vigentes OE2 y OE3

**Actualizado:** 2026-05-31
**Rama:** `smartcharger`
**Estado:** indice canonico para consultas de informes, metodologia y artefactos finales.

## Metodologia de investigacion

La tesis usa una sola metodologia de investigacion para todo el proyecto:

- Enfoque: cuantitativo
- Tipo: aplicada
- Nivel: explicativo-causal
- Diseno unico: cuasi-experimental por simulacion
- OE1, OE2 y OE3 son etapas del mismo diseno metodologico

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md` | Metodologia completa del proyecto PVBESSCAR |
| 2 | `README.md` | Resumen publico de metodologia, resultados y rutas vigentes |
| 3 | `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx` | Informe Word vigente generado desde fuentes canonicas |
| 4 | `scripts/reporting/generar_informe_tesis_oe3.py` | Script que regenera el DOCX vigente |

## OE3 - Control RL

El resultado vigente de seleccion de agente es **A2C** bajo el score multiobjetivo acumulado
de 50 episodios. PPO conserva lecturas puntuales favorables en F2, pero no reemplaza el
criterio operativo acumulado.

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` | Comparativa SAC/PPO/A2C y seleccion A2C |
| 2 | `reports/oe3/agents_comparison_canonical.json` | Fuente estructurada de ranking y metricas |
| 3 | `reports/oe3/agents_comparison_canonical.csv` | Tabla comparativa para hojas de calculo/reportes |
| 4 | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` | Analisis de CO2 directo e indirecto desde trazas |
| 5 | `reports/oe3/co2_trace_direct_indirect_summary.json` | Fuente estructurada del analisis CO2 |
| 6 | `reports/oe3/co2_trace_direct_indirect_summary.csv` | Tabla CSV del analisis CO2 |
| 7 | `reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md` | Patron operativo BESS/EV/pico por hora |
| 8 | `reports/oe3/COSTOS_ESTABILIDAD_OE3.md` | Costos tarifarios y estabilidad de red |
| 9 | `outputs/estadistica_oe3/reporte_estadistico_oe3.md` | Reporte estadistico inferencial vigente |
| 10 | `outputs/estadistica_oe3/tabla_completa_estadistica_oe3.csv` | Tabla estadistica completa |
| 11 | `outputs/docx/graficas/` | Figuras integradas al informe Word |

## OE2 - Dimensionamiento

| Prioridad | Documento | Uso |
|---:|---|---|
| 1 | `docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md` | Verificacion vigente de correcciones OE2 v5.2 actualizadas al pipeline v5.8 |
| 2 | `data/oe2/Generacionsolar/informe_generacion_solar_procedimiento_resultados_descriptivos.md` | Procedimiento y resultados descriptivos de generacion solar |
| 3 | `data/iquitos_ev_mall/dataset_config_v7.json` | Configuracion CityLearn v2 validada |

## Artefactos reemplazados

- `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v10.docx`
- `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v11.docx`
- `outputs/hypothesis_test/hypothesis_test_co2_figura_completa.png`

Reemplazo vigente:

- `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx`

Las salidas locales de entrenamiento bajo `outputs/*_training/` y `outputs/seccion52/`
son artefactos generados. No deben tratarse como documentos canonicos salvo que se
consoliden en `reports/oe3/` o se agreguen explicitamente a este indice.
