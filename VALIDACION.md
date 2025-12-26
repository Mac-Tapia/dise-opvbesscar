# Validacion - Tabla 9 e hipotesis (tesisvefinal)

Este archivo describe como validar el cumplimiento de la Tabla 9 y las
hipotesis sin modificar el texto aprobado de la tesis.

## Flujo recomendado
1) `python scripts/run_oe2_solar.py --config configs/default.yaml`
2) `python scripts/run_oe2_chargers.py --config configs/default.yaml`
3) `python scripts/run_oe1_location.py`
4) `python scripts/run_oe2_bess.py --config configs/default.yaml`
5) `python scripts/run_oe3_build_dataset.py --config configs/default.yaml`
6) `python scripts/run_oe3_simulate.py --config configs/default.yaml`
7) `python scripts/run_oe3_co2_table.py --config configs/default.yaml`
8) `python scripts/VALIDAR_CUMPLIMIENTO_ESTRICTO.py`

## Evidencia por objetivo e hipotesis

### HG (reduccion de CO2)
- Archivo: `analyses/oe3/co2_breakdown.csv`
- Criterio: `net_avoided_kgco2_y > 0`

### HE1 (ubicacion estrategica)
- Archivo: `data/interim/oe1/location_summary.json`
- Criterios: area techada, distancia a subestacion, flota en hora pico,
  tiempo de permanencia y capacidad de estacionamiento.

### HE2 (dimensionamiento PV, BESS y cargadores)
- Archivos:
  - `data/interim/oe2/solar/solar_results.json`
  - `data/interim/oe2/bess/bess_results.json`
  - `data/interim/oe2/chargers/chargers_results.json`
- Criterios: potencia FV, capacidad BESS (autonomia/DoD), potencia pico EV.

### HE3 (agente inteligente de gestion)
- Archivos:
  - `outputs/oe3/simulations/simulation_summary.json`
  - `analyses/oe3/agent_comparison.csv`
- Criterio: agente con menor CO2 (ranking = 1) frente al baseline.

## Salida de validacion automatizada
- `REPORTE_CUMPLIMIENTO.json` (resultado del script de validacion).
