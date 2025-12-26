# Mapeo operacional - Tabla 9 (tesisvefinal)

Este documento mapea cada dimension e indicador de la Tabla 9 al codigo,
parametros y salidas del proyecto. No modifica la redaccion aprobada en la tesis.

## Variable independiente: Diseno de la infraestructura de carga inteligente

### Dimension: Determinacion de la ubicacion estrategica
- Indicadores: area disponible (m2), capacidad de estacionamiento, accesibilidad/seguridad.
- Parametros: `configs/default.yaml` -> `oe1.site.*`
- Script: `scripts/run_oe1_location.py`
- Salidas:
  - `data/interim/oe1/location_summary.json`
  - `reports/oe1/location_summary.md`

### Dimension: Area techada y area de estacionamiento
- Indicadores: area techada util, % cobertura, restricciones fisicas.
- Parametros:
  - `configs/default.yaml` -> `oe1.site.coverage_required_pct`
  - `configs/default.yaml` -> `oe2.solar.area_total_m2`, `oe2.solar.factor_diseno`
- Script: `scripts/run_oe2_solar.py`
- Salidas:
  - `data/interim/oe2/solar/solar_results.json`
  - `data/interim/oe2/solar/solar_technical_report.md`

### Dimension: Disponibilidad de red electrica
- Indicadores: distancia a subestacion, capacidad estimada (kVA), continuidad.
- Parametros:
  - `configs/default.yaml` -> `oe1.site.distance_to_substation_m`
  - `configs/default.yaml` -> `oe1.grid_connection.*`
- Script: `scripts/run_oe1_location.py`
- Salidas:
  - `data/interim/oe1/location_summary.json` (required_capacity_kva, continuity)

## Dimensionamiento de capacidad (OE.2)

### Dimension: Potencia de generacion solar
- Indicadores: potencia FV (kWp), energia anual, area requerida.
- Codigo: `src/iquitos_citylearn/oe2/solar_pvlib.py`
- Script: `scripts/run_oe2_solar.py`
- Salidas:
  - `data/interim/oe2/solar/solar_results.json`
  - `data/interim/oe2/solar/pv_generation_timeseries.csv`
  - `data/interim/oe2/solar/pv_candidates_modules.csv`
  - `data/interim/oe2/solar/pv_candidates_inverters.csv`

### Dimension: Capacidad nominal de almacenamiento
- Indicadores: autonomia, DoD, capacidad nominal, verificacion vs picos.
- Codigo: `src/iquitos_citylearn/oe2/bess.py`
- Script: `scripts/run_oe2_bess.py`
- Salidas:
  - `data/interim/oe2/bess/bess_results.json` (capacity_kwh, autonomy_hours, peak_load_kw)
  - `data/interim/oe2/bess/bess_simulation_hourly.csv`

### Dimension: Cantidad de cargadores
- Indicador: potencia simultanea maxima y cantidad de cargadores.
- Codigo: `src/iquitos_citylearn/oe2/chargers.py`
- Script: `scripts/run_oe2_chargers.py`
- Salidas:
  - `data/interim/oe2/chargers/chargers_results.json` (peak_power_kw, n_chargers_recommended)
  - `data/interim/oe2/chargers/perfil_horario_carga.csv`

## Variable dependiente: Emisiones de CO2

### Dimension: Emisiones directas
- Indicadores: actividad base, emisiones base, emisiones por carga electrica.
- Codigo: `src/iquitos_citylearn/oe3/co2_table.py`
- Script: `scripts/run_oe3_co2_table.py`
- Salida: `analyses/oe3/co2_breakdown.csv` (direct_avoided_kgco2_y)

### Dimension: Emisiones indirectas
- Indicadores: energia FV efectiva y CO2 evitado por desplazamiento.
- Codigo: `src/iquitos_citylearn/oe3/co2_table.py`
- Script: `scripts/run_oe3_co2_table.py`
- Salida: `analyses/oe3/co2_breakdown.csv` (indirect_avoided_kgco2_y)

### Dimension: Reduccion neta de CO2
- Indicadores: CO2 evitado total y proyeccion.
- Codigo: `src/iquitos_citylearn/oe3/co2_table.py`
- Script: `scripts/run_oe3_co2_table.py`
- Salida: `analyses/oe3/co2_breakdown.csv` (net_avoided_kgco2_y, net_avoided_tco2_20y)

## Seleccion de agente inteligente de gestion de carga (OE.3)

### Dimension: Arquitectura de control
- Indicadores: control centralizado y recursos controlables.
- Codigo: `src/iquitos_citylearn/oe3/dataset_builder.py`
- Script: `scripts/run_oe3_build_dataset.py`
- Salida: `data/processed/citylearn/iquitos_ev_mall/schema.json`

### Dimension: Tipo de carga EV
- Indicadores: compatibilidad de carga y perfiles horarios.
- Codigo: `src/iquitos_citylearn/oe3/dataset_builder.py`
- Salidas:
  - `data/processed/citylearn/iquitos_ev_mall/charger_mall_*.csv`
  - `data/interim/oe2/chargers/chargers_hourly_profiles.csv`

### Dimension: Algoritmo de optimizacion (comparativo)
- Indicadores: KPIs y seleccion del agente con menor CO2.
- Codigo: `src/iquitos_citylearn/oe3/simulate.py`
- Script: `scripts/run_oe3_simulate.py`
- Salidas:
  - `outputs/oe3/simulations/simulation_summary.json`
  - `analyses/oe3/agent_comparison.csv`

## Validacion automatizada
- Script: `scripts/VALIDAR_CUMPLIMIENTO_ESTRICTO.py`
- Salida: `REPORTE_CUMPLIMIENTO.json`
