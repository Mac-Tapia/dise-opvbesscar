# Copilot Instructions for pvbesscar

## Current Canonical Context

**Updated:** 2026-06-04
**Branch:** `smartcharger`
**OE3 selected agent:** **A2C**
**Canonical report:** `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md`

Do not use older SAC/PPO selection snapshots for new reports. For any OE3 comparison, read:

- `reports/oe3/agents_comparison_canonical.json`
- `reports/oe3/agents_comparison_canonical.csv`
- `outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json`

## Project Purpose

`pvbesscar` optimizes EV charging for 38 sockets in Iquitos, Peru using solar PV, BESS and RL
agents (SAC/PPO/A2C) to reduce CO2 in an isolated grid (`0.4521 kg CO2/kWh`).

## Current Infrastructure

- Solar PV: 4,162 kWp DC / 3,201 kW AC, 5.819 GWh/año.
- BESS: 2,000 kWh / 400 kW.
- Chargers: 19 chargers x 2 sockets = 38 sockets.
- Fleet: 270 motos + 39 mototaxis per day.
- CityLearn v2: `obs_dim=19`, action dimension 3.

## OE3 Canonical Ranking

| Rank | Agent | F2 minimum (kg CO2/year) | Best episode | Reduction vs F0 | Multiobjective wins |
|---:|---|---:|---:|---:|---:|
| 1 | **A2C** | **3,642,436** | **2** | **48.36%** | **6/9** |
| 2 | PPO | 3,658,366 | 26 | 48.14% | 3/9 |
| 3 | SAC | 3,695,754 | 37 | 47.61% | 0/9 |

Normality tests are only used to choose statistical tests. Since Shapiro-Wilk rejects normality,
use non-parametric tests for inference.

## Useful Commands

```bash
python -m pytest tests -q
python scripts/generate_oe2_datasets.py --loader-only
python scripts/analysis/_ranking_oe3.py
python scripts/analysis/_seleccion_agente_oe3.py
python scripts/reporting/generar_tablas_oe3.py
```

## Guardrails

- Keep solar datasets at exactly 8,760 hourly rows.
- Use `validate_env_spaces(env)` before agent initialization.
- Do not regenerate reports from deprecated Word/HTML scripts; use `reports/oe3/`.
- Treat `outputs/*_training/` as generated artifacts, not canonical documentation.
