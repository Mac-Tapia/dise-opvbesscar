# OE3 - Reporte CO2 directo e indirecto desde trace

**Fecha de actualizacion:** 2026-05-31
**Fuente:** `outputs/*_training/trace_*.csv`

## Decision

Segun el criterio de **mayor CO2 evitado total** (`co2_avoided_indirect_kg + co2_avoided_direct_kg`), el mejor agente es **A2C** en el episodio trace **2**, con **2,519,848 kg CO2/año evitados**.

Si el criterio es **menor CO2 indirecto emitido por importacion de red** (`co2_grid_kg`), el mejor agente sigue siendo **A2C**, episodio trace **2**, con **3,642,436 kg CO2/año**.

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
| 1 | A2C | 2 | CO2 total evitado | 2,519,848 | 2,519,848 | 2,356,241 | 163,607 | 3,642,436 |
| 2 | PPO | 10 | CO2 total evitado | 2,482,187 | 2,482,187 | 2,262,755 | 219,433 | 3,692,268 |
| 3 | SAC | 5 | CO2 total evitado | 2,439,716 | 2,439,716 | 2,228,644 | 211,073 | 3,714,662 |

## Ranking por CO2 directo evitado

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | A2C | 39 | CO2 dir. evitado | 226,635 | 2,456,989 | 2,230,354 | 226,635 | 3,674,519 |
| 2 | PPO | 35 | CO2 dir. evitado | 225,617 | 2,465,351 | 2,239,734 | 225,617 | 3,664,527 |
| 3 | SAC | 21 | CO2 dir. evitado | 220,435 | 2,425,874 | 2,205,439 | 220,435 | 3,704,241 |

## Ranking por CO2 indirecto evitado

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | PPO | 1 | CO2 ind. evitado | 2,367,897 | 2,443,783 | 2,367,897 | 75,886 | 3,843,765 |
| 2 | A2C | 2 | CO2 ind. evitado | 2,356,241 | 2,519,848 | 2,356,241 | 163,607 | 3,642,436 |
| 3 | SAC | 1 | CO2 ind. evitado | 2,287,542 | 2,400,234 | 2,287,542 | 112,692 | 3,873,658 |

## Ranking por menor CO2 indirecto emitido

| Rank | Agente | Episodio trace | Criterio | Valor criterio | CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |
|---:|---|---:|---|---:|---:|---:|---:|---:|
| 1 | A2C | 2 | CO2 ind. emitido | 3,642,436 | 2,519,848 | 2,356,241 | 163,607 | 3,642,436 |
| 2 | PPO | 26 | CO2 ind. emitido | 3,658,366 | 2,465,574 | 2,245,411 | 220,163 | 3,658,366 |
| 3 | SAC | 37 | CO2 ind. emitido | 3,695,754 | 2,430,519 | 2,212,918 | 217,601 | 3,695,754 |

## Calidad de datos trace

| Agente | Filas totales | Episodios completos | Filas ignoradas | Observacion |
|---|---:|---:|---:|---|
| SAC | 438,000 | 50 | 0 | OK |
| PPO | 438,272 | 50 | 272 | se ignoro episodio parcial final |
| A2C | 438,272 | 50 | 272 | columna episode no incrementa; episodios reconstruidos |

## Conclusiones

- Para reduccion combinada directa + indirecta desde trace, **A2C** es el mejor agente.
- Para CO2 directo evitado aislado, **A2C** lidera con 226,635 kg CO2/año.
- Para CO2 indirecto evitado aislado, **PPO** lidera con 2,367,897 kg CO2/año.
- Para el criterio F2/CO2 indirecto residual minimo, **A2C** se mantiene como mejor agente.

## Archivos generados

- `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md`
- `reports/oe3/co2_trace_direct_indirect_summary.csv`
- `reports/oe3/co2_trace_direct_indirect_summary.json`
