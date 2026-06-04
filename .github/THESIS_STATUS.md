# PVBESSCAR - Thesis Status

**Updated:** 2026-06-04
**Branch:** `smartcharger`
**Status:** OE2 validated, OE3 canonical comparison updated.

## Canonical OE3 Result

The current selected agent is **A2C**, not SAC or PPO.

| Rank | Agent | F2 minimum (kg CO2/year) | Best episode | Reduction vs F0 | Multiobjective wins |
|---:|---|---:|---:|---:|---:|
| 1 | **A2C** | **3,642,436** | **2** | **48.36%** | **6/9** |
| 2 | PPO | 3,658,366 | 26 | 48.14% | 3/9 |
| 3 | SAC | 3,695,754 | 37 | 47.61% | 0/9 |

Canonical files:

- `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md`
- `reports/oe3/agents_comparison_canonical.json`
- `reports/oe3/agents_comparison_canonical.csv`

## Current OE2 Infrastructure

- Solar PV: 4,162 kWp DC / 3,201 kW AC.
- Annual solar generation: 5.819 GWh/año.
- BESS: 2,000 kWh / 400 kW.
- Chargers: 19 units / 38 sockets.
- Fleet: 270 motos + 39 mototaxis per day.
- Dataset resolution: 8,760 hourly rows.

## Validation Notes

- OE2 pipeline v5.8 verified in `docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md`.
- Statistical selection uses non-parametric tests because Shapiro-Wilk rejects normality.
- Historical Word/HTML/PDF artifacts that selected SAC/A2C have been removed or superseded.
