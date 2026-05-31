# OE3 - Reporte CO2 directo e indirecto desde trace

**Fecha de actualizacion:** 2026-05-30
**Fuente:** `outputs/*_training/trace_*.csv`

## Decision

Segun el criterio de **mayor CO2 evitado total** (`co2_avoided_indirect_kg + co2_avoided_direct_kg`), el mejor agente es **A2C** en el episodio trace **19**, con **2,523,717 kg CO2/año evitados**.

Si el criterio es **menor CO2 indirecto emitido por importacion de red** (`co2_grid_kg`), el mejor agente sigue siendo **PPO**, episodio trace **49**, con **3,657,484 kg CO2/año**.

## Metodologia

- Se reconstruyeron episodios por bloques de 8760 horas.
- Se usaron solo episodios completos; los episodios parciales finales se ignoraron.
- `co2_grid_kg` se interpreta como CO2 indirecto emitido por red electrica.
- `co2_avoided_indirect_kg` se interpreta como CO2 indirecto evitado.
- `co2_avoided_direct_kg` se interpreta como CO2 directo evitado.
- `co2_total_avoided_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg`.

## Ranking por CO2 evitado total

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | A2C | 19 | CO2 total evitado | 2,523,717 | 2,523,717 | 2,299,823 | 223,894 | 3,691,968 |
| 2 | PPO | 48 | CO2 total evitado | 2,469,954 | 2,469,954 | 2,242,799 | 227,155 | 3,660,595 |
| 3 | SAC | 9 | CO2 total evitado | 2,456,969 | 2,456,969 | 2,249,751 | 207,218 | 3,736,781 |

## Ranking por CO2 directo evitado

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | PPO | 48 | CO2 dir. evitado | 227,155 | 2,469,954 | 2,242,799 | 227,155 | 3,660,595 |
| 2 | A2C | 35 | CO2 dir. evitado | 225,136 | 2,461,967 | 2,236,832 | 225,136 | 3,670,317 |
| 3 | SAC | 14 | CO2 dir. evitado | 223,937 | 2,401,051 | 2,177,114 | 223,937 | 3,739,560 |

## Ranking por CO2 indirecto evitado

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | A2C | 1 | CO2 ind. evitado | 2,377,543 | 2,462,081 | 2,377,543 | 84,538 | 3,810,765 |
| 2 | PPO | 1 | CO2 ind. evitado | 2,365,179 | 2,442,920 | 2,365,179 | 77,741 | 3,844,560 |
| 3 | SAC | 1 | CO2 ind. evitado | 2,287,691 | 2,397,334 | 2,287,691 | 109,643 | 3,875,134 |

## Ranking por menor CO2 indirecto emitido

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | PPO | 49 | CO2 ind. emitido | 3,657,484 | 2,465,741 | 2,243,142 | 222,599 | 3,657,484 |
| 2 | A2C | 45 | CO2 ind. emitido | 3,659,010 | 2,468,179 | 2,246,403 | 221,776 | 3,659,010 |
| 3 | SAC | 33 | CO2 ind. emitido | 3,720,640 | 2,404,578 | 2,187,247 | 217,331 | 3,720,640 |

## Calidad de datos trace

| Agente | Filas totales | Episodios completos | Filas ignoradas | Observacion |
|---|---:|---:|---:|---|
| SAC | 438,000 | 50 | 0 | OK |
| PPO | 438,272 | 50 | 272 | se ignoro episodio parcial final |
| A2C | 438,272 | 50 | 272 | columna episode no incrementa; episodios reconstruidos |

## Conclusiones

- Para reduccion combinada directa + indirecta desde trace, **A2C** es el mejor agente.
- Para CO2 directo evitado aislado, **PPO** lidera con 227,155 kg CO2/año.
- Para CO2 indirecto evitado aislado, **A2C** lidera con 2,377,543 kg CO2/año.
- Para el criterio F2/CO2 indirecto residual minimo, **PPO** se mantiene como mejor agente.

## Archivos generados

- `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md`
- `reports/oe3/co2_trace_direct_indirect_summary.csv`
- `reports/oe3/co2_trace_direct_indirect_summary.json`
